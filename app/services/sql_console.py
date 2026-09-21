"""Read-only SQL console helpers for the Admin Database explorer."""

from __future__ import annotations

import json
import math
import re
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect, text

from app.services.query_cache import SQL_MUTATION_KEYWORDS

DEFAULT_ROWS = 200
MIN_ROWS = 1
MAX_ROWS = 10000
MAX_LATENCY_SAMPLES = 200
_TRAILING_SEMI = re.compile(r";+\s*$")


def clamp_row_limit(value: Any, default: int = DEFAULT_ROWS) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return max(MIN_ROWS, min(MAX_ROWS, limit))


def validate_readonly_sql(sql: str) -> str:
    """Return a single read-only statement, or raise ValueError."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL cannot be empty")
    statement = _TRAILING_SEMI.sub("", sql.strip())
    if not statement:
        raise ValueError("SQL cannot be empty")
    if ";" in statement:
        raise ValueError("Only a single SQL statement is allowed")
    upper = statement.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH") or upper.startswith("EXPLAIN")):
        raise ValueError("Only SELECT (or WITH / EXPLAIN) queries are allowed")
    for keyword in SQL_MUTATION_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", upper):
            raise ValueError(f"Blocked keyword: {keyword}")
    return statement


def _ensure_row_limit(sql: str, limit: int) -> str:
    if re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {int(limit)}"


def _cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)


def percentile(samples: list[float], pct: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    if pct >= 100:
        return round(ordered[-1], 3)
    if pct <= 0:
        return round(ordered[0], 3)
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        value = ordered[int(rank)]
    else:
        value = ordered[low] * (high - rank) + ordered[high] * (rank - low)
    return round(value, 3)


def list_tables_with_counts(db) -> list[dict[str, Any]]:
    inspector = inspect(db.engine)
    rows = []
    for name in inspector.get_table_names():
        quoted = db.engine.dialect.identifier_preparer.quote(name)
        count = db.session.execute(text(f"SELECT COUNT(*) FROM {quoted}")).scalar()
        columns = [col["name"] for col in inspector.get_columns(name)]
        rows.append({"name": name, "count": int(count or 0), "columns": columns})
    rows.sort(key=lambda item: item["name"])
    return rows


def run_readonly_query(db, sql: str, limit: int = DEFAULT_ROWS) -> dict[str, Any]:
    cap = clamp_row_limit(limit)
    statement = validate_readonly_sql(sql)
    limited = _ensure_row_limit(statement, cap)
    started = time.perf_counter()
    result = db.session.execute(text(limited))
    if not result.returns_rows:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "column_count": 0,
            "truncated": False,
            "sql": limited,
            "limit": cap,
            "elapsed_ms": elapsed_ms,
            "rows_per_sec": 0,
        }
    columns = list(result.keys())
    fetched = result.fetchmany(cap + 1)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    truncated = len(fetched) > cap
    rows = [[_cell(value) for value in row] for row in fetched[:cap]]
    row_count = len(rows)
    return {
        "columns": columns,
        "rows": rows,
        "row_count": row_count,
        "column_count": len(columns),
        "truncated": truncated,
        "sql": limited,
        "limit": cap,
        "elapsed_ms": elapsed_ms,
        "rows_per_sec": round(row_count / (elapsed_ms / 1000.0), 1) if elapsed_ms else None,
    }


def query_to_dict(row) -> dict[str, Any]:
    return row.to_dict()


def list_saved_queries(db) -> list[dict[str, Any]]:
    from app.models import SavedQuery

    rows = SavedQuery.query.order_by(SavedQuery.created_at.desc(), SavedQuery.id.desc()).all()
    return [query_to_dict(row) for row in rows]


def _load_samples(row) -> list[float]:
    raw = row.latency_samples_json
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    samples = []
    for item in data:
        try:
            samples.append(float(item))
        except (TypeError, ValueError):
            continue
    return samples


def _apply_latency_sample(row, elapsed_ms: float, row_count: int | None) -> None:
    samples = _load_samples(row)
    samples.append(float(elapsed_ms))
    samples = samples[-MAX_LATENCY_SAMPLES:]
    row.latency_samples_json = json.dumps(samples)
    row.latency_p50_ms = percentile(samples, 50)
    row.latency_p95_ms = percentile(samples, 95)
    row.latency_p99_ms = percentile(samples, 99)
    row.latency_p100_ms = percentile(samples, 100)
    row.last_run_ms = round(float(elapsed_ms), 3)
    row.last_run_at = datetime.now(timezone.utc).replace(tzinfo=None)
    row.run_count = (row.run_count or 0) + 1
    if row_count is not None:
        row.last_run_row_count = int(row_count)


def add_saved_query(
    db,
    name: str,
    sql: str,
    row_limit: Any = None,
    elapsed_ms: Any = None,
    row_count: Any = None,
) -> dict[str, Any]:
    from app.models import SavedQuery

    statement = validate_readonly_sql(sql)
    label = (name or "").strip() or "Untitled query"
    row = SavedQuery(
        name=label,
        sql=statement,
        row_limit=clamp_row_limit(row_limit),
        run_count=0,
    )
    if elapsed_ms is not None:
        try:
            _apply_latency_sample(row, float(elapsed_ms), int(row_count) if row_count is not None else None)
        except (TypeError, ValueError):
            pass
    db.session.add(row)
    db.session.commit()
    return query_to_dict(row)


def record_saved_query_run(db, query_id: int, elapsed_ms: float, row_count: int | None) -> dict[str, Any] | None:
    from app.models import SavedQuery

    row = db.session.get(SavedQuery, query_id)
    if row is None:
        return None
    _apply_latency_sample(row, elapsed_ms, row_count)
    db.session.commit()
    return query_to_dict(row)


def delete_saved_query(db, query_id: int) -> bool:
    from app.models import SavedQuery

    row = db.session.get(SavedQuery, query_id)
    if row is None:
        return False
    db.session.delete(row)
    db.session.commit()
    return True


def ensure_saved_query_columns(db) -> None:
    """Add latency columns to saved_queries if this database was created before they existed."""
    inspector = inspect(db.engine)
    if "saved_queries" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("saved_queries")}
    quoted = db.engine.dialect.identifier_preparer.quote("saved_queries")
    additions = (
        ("last_run_at", "DATETIME"),
        ("last_run_ms", "FLOAT"),
        ("last_run_row_count", "INTEGER"),
        ("run_count", "INTEGER DEFAULT 0"),
        ("latency_p50_ms", "FLOAT"),
        ("latency_p95_ms", "FLOAT"),
        ("latency_p99_ms", "FLOAT"),
        ("latency_p100_ms", "FLOAT"),
        ("latency_samples_json", "TEXT"),
    )
    changed = False
    for name, ddl in additions:
        if name in existing:
            continue
        db.session.execute(text(f"ALTER TABLE {quoted} ADD COLUMN {name} {ddl}"))
        changed = True
    if changed:
        db.session.commit()
