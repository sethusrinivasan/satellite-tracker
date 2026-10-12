"""Dynamic AI system prompt and few-shot translation configuration."""

import logging
from app import db
from app.models import SystemSetting

log = logging.getLogger(__name__)

PROMPT_SETTING_KEY = "ai_system_prompt"

DEFAULT_AI_SYSTEM_PROMPT = """You are a Text-to-SQL translator for a SQLite database.
Tables:
1. satellites:
   - id (INTEGER, PK)
   - norad_cat_id (INTEGER, Unique)
   - name (VARCHAR)
   - classification (VARCHAR)
   - int_designator (VARCHAR)
2. tle_elements:
   - id (INTEGER, PK)
   - satellite_id (INTEGER, FK to satellites.id)
   - epoch_datetime (DATETIME)
   - inclination_deg (FLOAT)
   - eccentricity (FLOAT)
   - mean_motion_rev_day (FLOAT)

Rules:
- Translate user's query into a valid SQLite SELECT query.
- Return ONLY the SQLite SELECT query. Do NOT include markdown code blocks (```sql) or explanations.
- Your query MUST select the 'norad_cat_id' column from the satellites table (e.g. SELECT s.norad_cat_id FROM satellites s ...).
- CRITICAL: If querying or ordering by any epoch parameters (inclination_deg, eccentricity, mean_motion_rev_day, epoch_datetime), you MUST explicitly JOIN tle_elements: JOIN tle_elements t ON s.id = t.satellite_id.
- Limit the query to 50 results if not specified.

Examples:
Request: Show me Starlink satellites with inclination greater than 53
Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id WHERE s.name LIKE '%STARLINK%' AND t.inclination_deg > 53 LIMIT 50;

Request: Find satellites with mean motion greater than 15
Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id WHERE t.mean_motion_rev_day > 15 LIMIT 50;

Request: Satellites in polar orbit with inclination near 90 degrees
Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id WHERE t.inclination_deg BETWEEN 85 AND 95 LIMIT 50;

Request: Satellites with high orbital eccentricity greater than 0.01
Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id WHERE t.eccentricity > 0.01 LIMIT 50;

Request: Active GPS satellites with inclination over 50 and low eccentricity
Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id WHERE s.name LIKE '%GPS%' AND t.inclination_deg > 50 AND t.eccentricity < 0.02 LIMIT 50;

Request: Fastest moving Low Earth Orbit satellites ordered by mean motion
Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id ORDER BY t.mean_motion_rev_day DESC LIMIT 50;"""


def get_ai_system_prompt() -> str:
    """Return the configured AI prompt or the built-in default."""
    try:
        setting = db.session.get(SystemSetting, PROMPT_SETTING_KEY)
        if setting and setting.value and setting.value.strip():
            return setting.value.strip()
    except Exception as exc:
        db.session.rollback()
        log.warning("[ai_prompt_service] Could not fetch system prompt: %s", exc)
    return DEFAULT_AI_SYSTEM_PROMPT.strip()


def set_ai_system_prompt(prompt_text: str) -> None:
    """Save or update the custom system prompt in SystemSetting."""
    cleaned = (prompt_text or "").strip()
    if not cleaned:
        reset_ai_system_prompt()
        return

    try:
        setting = db.session.get(SystemSetting, PROMPT_SETTING_KEY)
        if setting is None:
            setting = SystemSetting(key=PROMPT_SETTING_KEY, value=cleaned)
            db.session.add(setting)
        else:
            setting.value = cleaned
        db.session.commit()
        log.info("[ai_prompt_service] Updated dynamic AI system prompt.")
    except Exception as exc:
        db.session.rollback()
        log.error("[ai_prompt_service] Failed to persist system prompt: %s", exc)
        raise


def reset_ai_system_prompt() -> None:
    """Remove the custom system prompt and revert to default."""
    try:
        setting = db.session.get(SystemSetting, PROMPT_SETTING_KEY)
        if setting is not None:
            db.session.delete(setting)
            db.session.commit()
            log.info("[ai_prompt_service] Reset AI system prompt to default.")
    except Exception as exc:
        db.session.rollback()
        log.error("[ai_prompt_service] Failed to reset system prompt: %s", exc)
        raise


def is_custom_prompt_active() -> bool:
    """Return True if an administrator has customized the system prompt."""
    try:
        setting = db.session.get(SystemSetting, PROMPT_SETTING_KEY)
        return bool(setting and setting.value and setting.value.strip())
    except Exception:
        db.session.rollback()
        return False
