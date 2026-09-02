import os
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

CACHE_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ai_query_cache.json"
)


def _normalize_prompt(prompt: str) -> str:
    """Normalize prompt string for fuzzy matching (lowercase, stripped, single-spaced)."""
    return " ".join(prompt.strip().lower().split())


def load_query_cache() -> list:
    """Load query cache array from data/ai_query_cache.json."""
    if not os.path.exists(CACHE_FILE_PATH):
        return []
    try:
        with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("queries", [])
    except Exception as e:
        log.error("[Query Cache] Failed to read query cache file: %s", e)
        return []


def save_query_cache(queries: list) -> bool:
    """Persist query cache array to data/ai_query_cache.json."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
        with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"queries": queries}, f, indent=2)
        log.info("[Query Cache] Saved %d entries to %s", len(queries), CACHE_FILE_PATH)
        return True
    except Exception as e:
        log.error("[Query Cache] Failed to write query cache file: %s", e)
        return False


def get_cached_query(user_prompt: str) -> dict | None:
    """
    Search for a verified cached SQL entry matching the user prompt.
    Returns matched item dict or None.
    """
    norm_user = _normalize_prompt(user_prompt)
    queries = load_query_cache()

    for item in queries:
        if not item.get("verified", False):
            continue
        norm_cached = _normalize_prompt(item.get("prompt", ""))
        if norm_user == norm_cached:
            # Increment usage count and update timestamp
            item["use_count"] = item.get("use_count", 0) + 1
            save_query_cache(queries)
            return item

    return None


def cache_user_verified_query(prompt: str, sql: str, category: str = "verified_user") -> dict:
    """
    Cache a user-verified prompt -> SQL mapping into data/ai_query_cache.json.
    """
    norm_new = _normalize_prompt(prompt)
    queries = load_query_cache()

    # Check if entry already exists
    for item in queries:
        if _normalize_prompt(item.get("prompt", "")) == norm_new:
            item["sql"] = sql
            item["verified"] = True
            item["verified_at"] = datetime.now(timezone.utc).isoformat()
            item["use_count"] = item.get("use_count", 0) + 1
            save_query_cache(queries)
            return item

    # Add new entry
    new_entry = {
        "prompt": prompt.strip(),
        "sql": sql.strip(),
        "category": category,
        "verified": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "use_count": 1
    }
    queries.append(new_entry)
    save_query_cache(queries)
    return new_entry
