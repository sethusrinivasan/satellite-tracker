"""Unit and integration tests for Multi-Provider AI Service & Key Security."""

import os
from unittest.mock import MagicMock, patch

import pytest
from app import db
from app.models import Satellite, SystemSetting, TLEElement
from app.services.ai_provider_service import (
    check_provider_connection,
    generate_sql_with_fallback,
    get_ai_config,
    mask_key,
    sanitize_error_message,
    save_ai_config,
)


def _login_admin(client):
    with client.session_transaction() as sess:
        sess["admin_user"] = {
            "email": "dev-admin@localhost",
            "name": "Dev Admin",
            "is_dev_bypass": True,
        }


def test_mask_key():
    assert mask_key(None) == ""
    assert mask_key("") == ""
    assert mask_key("short") == "••••••••"
    assert mask_key("AIzaSyB123456789") == "AIz...6789"
    assert mask_key("sk-proj-1234567890abcdef") == "sk-...cdef"


def test_sanitize_error_message():
    assert sanitize_error_message(None) == "Unknown AI provider error"
    
    # URL query parameter with key
    msg1 = "Failed to connect: https://generativelanguage.googleapis.com/v1beta?key=AIzaSyB123456789XYZ"
    sanitized1 = sanitize_error_message(msg1)
    assert "AIzaSyB123456789XYZ" not in sanitized1
    assert "key=[REDACTED]" in sanitized1

    # Authorization Bearer
    msg2 = "HTTP 401 Unauthorized with header Bearer sk-1234567890abcdef"
    sanitized2 = sanitize_error_message(msg2)
    assert "sk-1234567890abcdef" not in sanitized2
    assert "Bearer [REDACTED]" in sanitized2


def test_save_and_get_ai_config(app):
    with app.app_context():
        save_ai_config(
            provider="gemini",
            model="gemini-2.0-flash",
            gemini_key="AIzaSyTesting123456",
            ollama_url="http://custom-ollama:11434",
        )
        cfg = get_ai_config()
        assert cfg["provider"] == "gemini"
        assert cfg["model"] == "gemini-2.0-flash"
        assert cfg["gemini_configured"] is True
        assert cfg["gemini_key_masked"] == "AIz...3456"
        assert cfg["ollama_url"] == "http://custom-ollama:11434"


def test_generate_sql_gemini_mocked(app):
    with app.app_context():
        save_ai_config(provider="gemini", gemini_key="fake-test-key")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "```sql\nSELECT norad_cat_id FROM satellites WHERE name LIKE '%STARLINK%';\n```"}]
                    }
                }
            ]
        }
        with patch("requests.post", return_value=mock_resp):
            sql, provider, dur = generate_sql_with_fallback("Find Starlink")
            assert "SELECT norad_cat_id FROM satellites" in sql
            assert "gemini" in provider
            assert dur >= 0


def test_generate_sql_openai_mocked(app):
    with app.app_context():
        save_ai_config(provider="openai", openai_key="sk-fake-openai-key")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "SELECT norad_cat_id FROM satellites LIMIT 10;"
                    }
                }
            ]
        }
        with patch("requests.post", return_value=mock_resp):
            sql, provider, dur = generate_sql_with_fallback("List 10 satellites")
            assert "SELECT norad_cat_id FROM satellites LIMIT 10;" == sql
            assert "openai" in provider


def test_generate_sql_ollama_mocked(app):
    with app.app_context():
        save_ai_config(provider="ollama", ollama_url="http://localhost:11434")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "SELECT s.norad_cat_id FROM satellites s;"
        }
        with patch("requests.post", return_value=mock_resp):
            sql, provider, dur = generate_sql_with_fallback("List all satellites")
            assert "SELECT s.norad_cat_id FROM satellites s;" == sql
            assert "ollama" in provider


def test_check_provider_connection_mocked(app):
    with app.app_context():
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "SELECT norad_cat_id FROM satellites WHERE norad_cat_id = 25544;"}]}}]
        }
        with patch("requests.post", return_value=mock_resp):
            result = check_provider_connection("gemini", api_key="AIzaSyTestKey1234")
            assert result["ok"] is True
            assert "25544" in result["sql"]
            assert result["provider"] == "gemini"


def test_admin_ai_provider_routes(client, app):
    _login_admin(client)

    # POST update config
    resp = client.post(
        "/admin/ai-provider",
        data={
            "provider": "ollama",
            "ollama_url": "http://127.0.0.1:11434",
            "model": "qwen2.5-coder",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        cfg = get_ai_config()
        assert cfg["provider"] == "ollama"
        assert cfg["ollama_url"] == "http://127.0.0.1:11434"

    # POST test connection (mocked)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "SELECT norad_cat_id FROM satellites;"}
    with patch("requests.post", return_value=mock_resp):
        test_resp = client.post(
            "/admin/ai-provider/test",
            json={"provider": "ollama", "base_url": "http://127.0.0.1:11434"},
        )
        assert test_resp.status_code == 200
        assert test_resp.get_json()["ok"] is True


def test_clean_sql_output():
    from app.services.ai_provider_service import _clean_sql_output

    assert _clean_sql_output("SELECT * FROM satellites;") == "SELECT * FROM satellites;"
    assert _clean_sql_output("```sql\nSELECT * FROM satellites;\n```") == "SELECT * FROM satellites;"
    assert _clean_sql_output("```\nSELECT 1;\n```") == "SELECT 1;"
    assert _clean_sql_output("Here is the SQL:\n```sql\nSELECT * FROM satellites\n```") == "SELECT * FROM satellites;"
    # Pathological ReDoS probe string (starts with ``` followed by 50,000 spaces without closing ```)
    probe = "```" + " " * 50000
    assert _clean_sql_output(probe) == ";"
