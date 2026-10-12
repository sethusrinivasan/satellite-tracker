"""
Multi-Provider AI Service for Natural Language Text-to-SQL Orbital Discovery.

Provides flexible, pluggable model execution across:
  - Local GGUF (llama-cpp-python / Qwen2.5-Coder)
  - Local Ollama (in-cluster/local loopback REST API, zero cloud keys)
  - Google Gemini (Gemini 1.5 / 2.0 REST API)
  - OpenAI (Chat Completions REST API)
  - Anthropic (Messages REST API)
  - Custom OpenAI-compatible providers (Groq, Together, DeepSeek, LocalAI)
  - Auto-fallback chain (Configured Provider -> Local Ollama -> Local GGUF)

Security Guarantees:
  - API keys are NEVER logged or printed to stdout.
  - Exception messages are sanitized to strip URLs containing key query parameters
    and authorization tokens before reaching error handlers.
  - Keys returned to API consumers or Admin UI are strictly masked (e.g. sk-...a1b2).
  - Keys are loaded from environment variables or encrypted/protected datastore settings.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Tuple

import requests
from app import db
from app.models import SystemSetting
from app.services.ai_prompt_service import get_ai_system_prompt

logger = logging.getLogger(__name__)

# Setting keys in SystemSetting table
SETTING_PROVIDER = "ai_provider"
SETTING_MODEL = "ai_model"
SETTING_GEMINI_KEY = "ai_gemini_key"
SETTING_OPENAI_KEY = "ai_openai_key"
SETTING_ANTHROPIC_KEY = "ai_anthropic_key"
SETTING_OLLAMA_URL = "ai_ollama_url"
SETTING_CUSTOM_URL = "ai_custom_url"
SETTING_CUSTOM_KEY = "ai_custom_key"

DEFAULT_PROVIDER = "auto"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"


def mask_key(key: str | None) -> str:
    """Mask a sensitive API key for safe display in logs or UI (e.g. 'sk-...abcd')."""
    if not key or len(key) < 6:
        return "••••••••" if key else ""
    prefix = key[:3] if len(key) > 8 else key[:2]
    suffix = key[-4:]
    return f"{prefix}...{suffix}"


def sanitize_error_message(msg: str) -> str:
    """Remove potential API keys, auth headers, and query param tokens from error messages."""
    if not msg:
        return "Unknown AI provider error"
    # Mask key=... or api_key=... query strings
    cleaned = re.sub(r"(key|api_key|token|auth)=([a-zA-Z0-9_\-\.]{8,})", r"\1=[REDACTED]", msg)
    # Mask Bearer tokens
    cleaned = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{8,}", r"\1[REDACTED]", cleaned)
    # Mask raw long sk- or AIza tokens
    cleaned = re.sub(r"(sk-[a-zA-Z0-9_\-]{8,})", r"[REDACTED_API_KEY]", cleaned)
    cleaned = re.sub(r"(AIza[a-zA-Z0-9_\-]{8,})", r"[REDACTED_API_KEY]", cleaned)
    return cleaned


def get_setting_or_env(setting_key: str, env_var: str, default: str = "") -> str:
    """Get configuration with priority: SystemSetting database -> Environment variable -> Default."""
    try:
        row = db.session.get(SystemSetting, setting_key)
        if row and row.value and row.value.strip():
            return row.value.strip()
    except Exception as exc:
        db.session.rollback()
        logger.debug("[ai_provider] Could not read setting %s: %s", setting_key, exc)

    return os.environ.get(env_var, default).strip()


def get_ai_config() -> dict[str, Any]:
    """Return active AI provider configuration with masked credentials for safe inspection."""
    provider = get_setting_or_env(SETTING_PROVIDER, "AI_PROVIDER", DEFAULT_PROVIDER).lower()
    gemini_key = get_setting_or_env(SETTING_GEMINI_KEY, "GEMINI_API_KEY")
    openai_key = get_setting_or_env(SETTING_OPENAI_KEY, "OPENAI_API_KEY")
    anthropic_key = get_setting_or_env(SETTING_ANTHROPIC_KEY, "ANTHROPIC_API_KEY")
    custom_key = get_setting_or_env(SETTING_CUSTOM_KEY, "CUSTOM_AI_API_KEY")
    ollama_url = get_setting_or_env(SETTING_OLLAMA_URL, "OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
    custom_url = get_setting_or_env(SETTING_CUSTOM_URL, "CUSTOM_AI_BASE_URL")
    model_override = get_setting_or_env(SETTING_MODEL, "AI_MODEL_NAME")

    return {
        "provider": provider,
        "model": model_override,
        "ollama_url": ollama_url,
        "custom_url": custom_url,
        "gemini_configured": bool(gemini_key),
        "openai_configured": bool(openai_key),
        "anthropic_configured": bool(anthropic_key),
        "custom_configured": bool(custom_key),
        "gemini_key_masked": mask_key(gemini_key),
        "openai_key_masked": mask_key(openai_key),
        "anthropic_key_masked": mask_key(anthropic_key),
        "custom_key_masked": mask_key(custom_key),
    }


def save_ai_config(
    provider: str | None = None,
    model: str | None = None,
    gemini_key: str | None = None,
    openai_key: str | None = None,
    anthropic_key: str | None = None,
    ollama_url: str | None = None,
    custom_url: str | None = None,
    custom_key: str | None = None,
) -> None:
    """Save user-configured AI settings into SystemSetting securely."""
    entries = {
        SETTING_PROVIDER: provider,
        SETTING_MODEL: model,
        SETTING_GEMINI_KEY: gemini_key,
        SETTING_OPENAI_KEY: openai_key,
        SETTING_ANTHROPIC_KEY: anthropic_key,
        SETTING_OLLAMA_URL: ollama_url,
        SETTING_CUSTOM_URL: custom_url,
        SETTING_CUSTOM_KEY: custom_key,
    }
    for k, v in entries.items():
        if v is not None:
            # Strip whitespace
            val_clean = v.strip()
            # Do not overwrite with placeholder mask
            if val_clean and "••••" in val_clean:
                continue
            row = db.session.get(SystemSetting, k)
            if row:
                row.value = val_clean
            else:
                db.session.add(SystemSetting(key=k, value=val_clean))
    db.session.commit()
    logger.info("[ai_provider] Updated AI configuration in datastore")


def _clean_sql_output(raw_text: str) -> str:
    """Clean markdown code fences, comments, and whitespace to extract raw SQL without backtracking regex."""
    cleaned = raw_text.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 3:
            fence_content = parts[1].strip()
            if fence_content.lower().startswith("sql"):
                fence_content = fence_content[3:].strip()
            cleaned = fence_content
        else:
            cleaned = cleaned.replace("```", "").strip()
    cleaned = cleaned.rstrip(";") + ";"
    return cleaned


# ── Provider Implementation Functions ────────────────────────────────────────

def _call_gemini(user_prompt: str, api_key: str, model_name: str) -> str:
    """Execute Gemini REST API for Text-to-SQL generation."""
    system_prompt = get_ai_system_prompt()
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"User Request: {user_prompt}\nReturn ONLY the single SQLite SELECT query:"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 200,
        }
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        err_msg = sanitize_error_message(resp.text)
        raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {err_msg}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned empty candidate response")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts or "text" not in parts[0]:
        raise RuntimeError("Gemini returned invalid response structure")
    return _clean_sql_output(parts[0]["text"])


def _call_openai_compatible(
    user_prompt: str,
    base_url: str,
    api_key: str,
    model_name: str,
    extra_headers: dict[str, str] | None = None,
) -> str:
    """Execute OpenAI-compatible Chat Completions REST endpoint."""
    system_prompt = get_ai_system_prompt()
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Request: {user_prompt}\nReturn ONLY the single SQLite SELECT query:"},
        ],
        "temperature": 0.1,
        "max_tokens": 200,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        err_msg = sanitize_error_message(resp.text)
        raise RuntimeError(f"API returned HTTP {resp.status_code}: {err_msg}")

    data = resp.json()
    choices = data.get("choices", [])
    if not choices or "message" not in choices[0]:
        raise RuntimeError("API returned empty choices response")
    content = choices[0]["message"].get("content", "")
    return _clean_sql_output(content)


def _call_anthropic(user_prompt: str, api_key: str, model_name: str) -> str:
    """Execute Anthropic Messages REST API for Text-to-SQL generation."""
    system_prompt = get_ai_system_prompt()
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": model_name,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": f"User Request: {user_prompt}\nReturn ONLY the single SQLite SELECT query:"}
        ],
        "max_tokens": 200,
        "temperature": 0.1,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        err_msg = sanitize_error_message(resp.text)
        raise RuntimeError(f"Anthropic API returned HTTP {resp.status_code}: {err_msg}")

    data = resp.json()
    content_list = data.get("content", [])
    if not content_list or "text" not in content_list[0]:
        raise RuntimeError("Anthropic returned empty content response")
    return _clean_sql_output(content_list[0]["text"])


def _call_ollama(user_prompt: str, base_url: str, model_name: str) -> str:
    """Execute local Ollama REST endpoint."""
    system_prompt = get_ai_system_prompt()
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model_name,
        "system": system_prompt,
        "prompt": f"User Request: {user_prompt}\nReturn ONLY the single SQLite SELECT query:",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 200,
        }
    }
    resp = requests.post(url, json=payload, timeout=20)
    if resp.status_code != 200:
        err_msg = sanitize_error_message(resp.text)
        raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {err_msg}")

    data = resp.json()
    response_text = data.get("response", "")
    if not response_text:
        raise RuntimeError("Ollama returned empty response")
    return _clean_sql_output(response_text)


def _call_local_gguf(user_prompt: str, report_route_get_llm: Any = None) -> str:
    """Execute local in-process GGUF model via llama-cpp-python."""
    system_prompt = get_ai_system_prompt()
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
    
    if report_route_get_llm is None:
        from app.routes.report import _get_llm
        llm = _get_llm()
    else:
        llm = report_route_get_llm()

    resp = llm(
        prompt,
        max_tokens=150,
        stop=["<|im_end|>"],
        temperature=0.1,
    )
    text = resp["choices"][0]["text"].strip()
    return _clean_sql_output(text)


# ── Unified Dispatcher with Resilient Fallback ────────────────────────────────

def generate_sql_with_fallback(
    user_prompt: str,
    local_llm_getter: Any = None
) -> Tuple[str, str, float]:
    """
    Generate SQL query using the configured AI provider with graceful fallback.
    Returns: (sql_query, provider_used, inference_elapsed_sec)
    """
    config = get_ai_config()
    provider = config["provider"]
    model_override = config["model"]

    gemini_key = get_setting_or_env(SETTING_GEMINI_KEY, "GEMINI_API_KEY")
    openai_key = get_setting_or_env(SETTING_OPENAI_KEY, "OPENAI_API_KEY")
    anthropic_key = get_setting_or_env(SETTING_ANTHROPIC_KEY, "ANTHROPIC_API_KEY")
    ollama_url = config["ollama_url"] or DEFAULT_OLLAMA_URL
    custom_url = config["custom_url"]
    custom_key = get_setting_or_env(SETTING_CUSTOM_KEY, "CUSTOM_AI_API_KEY")

    t0 = time.perf_counter()
    errors: list[str] = []

    # Priority 1: Direct Provider Dispatch if explicitly requested
    if provider == "gemini":
        if not gemini_key:
            raise ValueError("Gemini API key is not configured.")
        model = model_override or DEFAULT_GEMINI_MODEL
        sql = _call_gemini(user_prompt, gemini_key, model)
        return sql, f"gemini ({model})", round(time.perf_counter() - t0, 3)

    elif provider == "openai":
        if not openai_key:
            raise ValueError("OpenAI API key is not configured.")
        model = model_override or DEFAULT_OPENAI_MODEL
        sql = _call_openai_compatible(user_prompt, "https://api.openai.com/v1", openai_key, model)
        return sql, f"openai ({model})", round(time.perf_counter() - t0, 3)

    elif provider == "anthropic":
        if not anthropic_key:
            raise ValueError("Anthropic API key is not configured.")
        model = model_override or DEFAULT_ANTHROPIC_MODEL
        sql = _call_anthropic(user_prompt, anthropic_key, model)
        return sql, f"anthropic ({model})", round(time.perf_counter() - t0, 3)

    elif provider == "ollama":
        model = model_override or DEFAULT_OLLAMA_MODEL
        sql = _call_ollama(user_prompt, ollama_url, model)
        return sql, f"ollama ({model})", round(time.perf_counter() - t0, 3)

    elif provider == "custom":
        if not custom_url:
            raise ValueError("Custom AI base URL is not configured.")
        model = model_override or "default"
        sql = _call_openai_compatible(user_prompt, custom_url, custom_key, model)
        return sql, f"custom ({model})", round(time.perf_counter() - t0, 3)

    elif provider == "local_gguf":
        sql = _call_local_gguf(user_prompt, local_llm_getter)
        return sql, "local_gguf (Qwen2.5-Coder)", round(time.perf_counter() - t0, 3)

    # Priority 2: Auto Fallback Chain
    # Attempt in order: Gemini -> OpenAI -> Anthropic -> Local Ollama -> Local GGUF
    if gemini_key:
        try:
            model = model_override or DEFAULT_GEMINI_MODEL
            sql = _call_gemini(user_prompt, gemini_key, model)
            return sql, f"gemini ({model})", round(time.perf_counter() - t0, 3)
        except Exception as e:
            err = sanitize_error_message(str(e))
            logger.warning("[ai_provider] Gemini failed in auto fallback: %s", err)
            errors.append(f"Gemini: {err}")

    if openai_key:
        try:
            model = model_override or DEFAULT_OPENAI_MODEL
            sql = _call_openai_compatible(user_prompt, "https://api.openai.com/v1", openai_key, model)
            return sql, f"openai ({model})", round(time.perf_counter() - t0, 3)
        except Exception as e:
            err = sanitize_error_message(str(e))
            logger.warning("[ai_provider] OpenAI failed in auto fallback: %s", err)
            errors.append(f"OpenAI: {err}")

    if anthropic_key:
        try:
            model = model_override or DEFAULT_ANTHROPIC_MODEL
            sql = _call_anthropic(user_prompt, anthropic_key, model)
            return sql, f"anthropic ({model})", round(time.perf_counter() - t0, 3)
        except Exception as e:
            err = sanitize_error_message(str(e))
            logger.warning("[ai_provider] Anthropic failed in auto fallback: %s", err)
            errors.append(f"Anthropic: {err}")

    # Try local Ollama if responding
    try:
        model = model_override or DEFAULT_OLLAMA_MODEL
        sql = _call_ollama(user_prompt, ollama_url, model)
        return sql, f"ollama ({model})", round(time.perf_counter() - t0, 3)
    except Exception as e:
        err = sanitize_error_message(str(e))
        logger.debug("[ai_provider] Ollama check failed in auto fallback: %s", err)
        errors.append(f"Ollama: {err}")

    # Try local in-process GGUF
    try:
        sql = _call_local_gguf(user_prompt, local_llm_getter)
        return sql, "local_gguf (Qwen2.5-Coder)", round(time.perf_counter() - t0, 3)
    except Exception as e:
        err = sanitize_error_message(str(e))
        logger.warning("[ai_provider] Local GGUF failed in auto fallback: %s", err)
        errors.append(f"Local GGUF: {err}")

    raise RuntimeError(
        "No AI provider succeeded. Ensure a local model is downloaded in Admin or configure an API key for Gemini, OpenAI, or Ollama. (Details: " + "; ".join(errors) + ")"
    )


def check_provider_connection(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Test connection and minimal inference for a selected provider without leaking keys."""
    test_prompt = "Find ISS"
    clean_key = (api_key or "").strip()
    # Resolve key if masked placeholder was provided
    if "••••" in clean_key or not clean_key:
        if provider == "gemini":
            clean_key = get_setting_or_env(SETTING_GEMINI_KEY, "GEMINI_API_KEY")
        elif provider == "openai":
            clean_key = get_setting_or_env(SETTING_OPENAI_KEY, "OPENAI_API_KEY")
        elif provider == "anthropic":
            clean_key = get_setting_or_env(SETTING_ANTHROPIC_KEY, "ANTHROPIC_API_KEY")
        elif provider == "custom":
            clean_key = get_setting_or_env(SETTING_CUSTOM_KEY, "CUSTOM_AI_API_KEY")

    t0 = time.perf_counter()
    try:
        if provider == "gemini":
            if not clean_key:
                return {"ok": False, "error": "Gemini API key is required"}
            target_model = model or DEFAULT_GEMINI_MODEL
            sql = _call_gemini(test_prompt, clean_key, target_model)
            return {"ok": True, "provider": provider, "model": target_model, "sql": sql, "latency_sec": round(time.perf_counter() - t0, 3)}

        elif provider == "openai":
            if not clean_key:
                return {"ok": False, "error": "OpenAI API key is required"}
            target_model = model or DEFAULT_OPENAI_MODEL
            sql = _call_openai_compatible(test_prompt, "https://api.openai.com/v1", clean_key, target_model)
            return {"ok": True, "provider": provider, "model": target_model, "sql": sql, "latency_sec": round(time.perf_counter() - t0, 3)}

        elif provider == "anthropic":
            if not clean_key:
                return {"ok": False, "error": "Anthropic API key is required"}
            target_model = model or DEFAULT_ANTHROPIC_MODEL
            sql = _call_anthropic(test_prompt, clean_key, target_model)
            return {"ok": True, "provider": provider, "model": target_model, "sql": sql, "latency_sec": round(time.perf_counter() - t0, 3)}

        elif provider == "ollama":
            target_url = base_url or DEFAULT_OLLAMA_URL
            target_model = model or DEFAULT_OLLAMA_MODEL
            sql = _call_ollama(test_prompt, target_url, target_model)
            return {"ok": True, "provider": provider, "model": target_model, "sql": sql, "latency_sec": round(time.perf_counter() - t0, 3)}

        elif provider == "custom":
            if not base_url:
                return {"ok": False, "error": "Custom endpoint URL is required"}
            target_model = model or "default"
            sql = _call_openai_compatible(test_prompt, base_url, clean_key, target_model)
            return {"ok": True, "provider": provider, "model": target_model, "sql": sql, "latency_sec": round(time.perf_counter() - t0, 3)}

        elif provider == "local_gguf":
            sql = _call_local_gguf(test_prompt)
            return {"ok": True, "provider": provider, "model": "Qwen2.5-Coder", "sql": sql, "latency_sec": round(time.perf_counter() - t0, 3)}

        else:
            return {"ok": False, "error": f"Unsupported provider: {provider}"}

    except requests.Timeout:
        logger.warning("Provider connection test timed out for provider: %s", provider)
        return {"ok": False, "error": "Connection timed out while contacting the provider endpoint.", "latency_sec": round(time.perf_counter() - t0, 3)}
    except requests.ConnectionError:
        logger.warning("Provider connection failed to reach provider: %s", provider)
        return {"ok": False, "error": "Unable to connect to provider endpoint. Please verify URL and network connectivity.", "latency_sec": round(time.perf_counter() - t0, 3)}
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        logger.warning("Provider connection test failed for %s: %s", provider, sanitized)
        return {"ok": False, "error": "Provider connection test failed. Please verify provider settings and credentials.", "latency_sec": round(time.perf_counter() - t0, 3)}
