"""Persisted feature flags with Vercel and platform-aware defaults."""

import os
from app.services.cache_backends import is_valkey_supported_platform

FEATURES = {
    "offline_ai_search": "Offline AI natural-language search",
    "ai_model_management": "GGUF model download and management",
    "system_telemetry": "Host and container telemetry",
    "valkey_cache": "Valkey high-performance memory cache",
}


def _defaults() -> dict[str, bool]:
    disabled_on_vercel = bool(os.environ.get("VERCEL"))
    flags = {
        name: not disabled_on_vercel
        for name in ("offline_ai_search", "ai_model_management", "system_telemetry")
    }

    valkey_env = os.environ.get("ENABLE_VALKEY_CACHE") or os.environ.get("USE_EMBEDDED_VALKEY")
    if valkey_env is not None:
        flags["valkey_cache"] = valkey_env.lower() in ("1", "true", "yes", "on")
    else:
        flags["valkey_cache"] = is_valkey_supported_platform()

    return flags



def get_feature_flags() -> dict[str, bool]:
    """Return persisted flags, falling back to environment-aware defaults."""
    from app import db
    from app.models import SystemSetting

    flags = _defaults()
    try:
        from flask import has_app_context

        if has_app_context():
            for name in FEATURES:
                setting = db.session.get(SystemSetting, f"feature:{name}")
                if setting is not None:
                    flags[name] = setting.value == "1"
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return flags
    return flags


def feature_enabled(name: str) -> bool:
    return get_feature_flags().get(name, False)


def set_feature_flags(values: dict[str, bool]) -> None:
    """Persist only known feature flags."""
    from app import db
    from app.models import SystemSetting

    for name in FEATURES:
        if name not in values:
            continue
        key = f"feature:{name}"
        setting = db.session.get(SystemSetting, key)
        if setting is None:
            setting = SystemSetting(key=key, value="1" if values[name] else "0")
            db.session.add(setting)
        else:
            setting.value = "1" if values[name] else "0"
    db.session.commit()

    if "valkey_cache" in values:
        try:
            from app.services import overlay_cache

            overlay_cache.reset_runtime_state()
        except Exception:
            pass

