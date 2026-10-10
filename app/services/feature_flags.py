"""Persisted feature flags with Vercel-safe defaults."""

import os

FEATURES = {
    "offline_ai_search": "Offline AI natural-language search",
    "ai_model_management": "GGUF model download and management",
    "system_telemetry": "Host and container telemetry",
}


def _defaults() -> dict[str, bool]:
    disabled_on_vercel = bool(os.environ.get("VERCEL"))
    return {
        name: not disabled_on_vercel
        for name in FEATURES
    }


def get_feature_flags() -> dict[str, bool]:
    """Return persisted flags, falling back to environment-aware defaults."""
    from app import db
    from app.models import SystemSetting

    flags = _defaults()
    try:
        for name in FEATURES:
            setting = db.session.get(SystemSetting, f"feature:{name}")
            if setting is not None:
                flags[name] = setting.value == "1"
    except Exception:
        db.session.rollback()
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
