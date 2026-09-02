from flask import Blueprint, request, render_template, jsonify
from sqlalchemy import or_, func
from app.models import Satellite, TLEElement, Upload
from app import db
from app.routes.auth import admin_required

report_bp = Blueprint("report", __name__)


@report_bp.route("/report", methods=["GET"])
def report():
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    satellites = []
    total = 0

    if query:
        # Search by name (partial, case-insensitive) or NORAD ID
        base_q = Satellite.query.filter(
            or_(
                Satellite.name.ilike(f"%{query}%"),
                Satellite.norad_cat_id == _try_int(query),
            )
        )
        total = base_q.count()
        satellites = base_q.order_by(Satellite.name).offset((page - 1) * per_page).limit(per_page).all()

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "report.html",
        satellites=satellites,
        query=query,
        page=page,
        total=total,
        total_pages=total_pages,
        per_page=per_page,
    )


@report_bp.route("/report/satellite/<int:norad_id>", methods=["GET"])
def satellite_detail(norad_id: int):
    satellite = Satellite.query.filter_by(norad_cat_id=norad_id).first_or_404()
    elements = (
        TLEElement.query.filter_by(satellite_id=satellite.id)
        .order_by(TLEElement.epoch_datetime.desc())
        .all()
    )
    return render_template("satellite_detail.html", satellite=satellite, elements=elements)


@report_bp.route("/tracker", methods=["GET"])
def tracker():
    ids_raw = request.args.get("ids", "").strip()
    tracked = []
    if ids_raw:
        try:
            norad_ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip().isdigit()]
            for norad_id in norad_ids:
                sat = Satellite.query.filter_by(norad_cat_id=norad_id).first()
                if sat:
                    tle = (
                        TLEElement.query.filter_by(satellite_id=sat.id)
                        .order_by(TLEElement.epoch_datetime.desc())
                        .first()
                    )
                    if tle:
                        tracked.append({
                            "satellite": sat,
                            "tle": tle
                        })
        except Exception:
            pass

    return render_template("tracker.html", tracked=tracked)


@report_bp.route("/api/satellite/<int:norad_id>/elements", methods=["GET"])
def satellite_elements_api(norad_id: int):
    """JSON API — returns all TLE elements for a satellite."""
    satellite = Satellite.query.filter_by(norad_cat_id=norad_id).first_or_404()
    elements = (
        TLEElement.query.filter_by(satellite_id=satellite.id)
        .order_by(TLEElement.epoch_datetime.desc())
        .all()
    )
    return jsonify({
        "satellite": {
            "norad_cat_id": satellite.norad_cat_id,
            "name": satellite.name,
            "classification": satellite.classification,
            "int_designator": satellite.int_designator,
        },
        "elements": [_element_to_dict(e) for e in elements],
    })


@report_bp.route("/stats", methods=["GET"])
def stats():
    total_satellites = Satellite.query.count()
    total_elements = TLEElement.query.count()
    total_uploads = Upload.query.count()
    recent_uploads = Upload.query.order_by(Upload.upload_time.desc()).limit(5).all()
    return render_template(
        "stats.html",
        total_satellites=total_satellites,
        total_elements=total_elements,
        total_uploads=total_uploads,
        recent_uploads=recent_uploads,
    )


def _try_int(s: str):
    try:
        return int(s)
    except ValueError:
        return -1


def _element_to_dict(e: TLEElement) -> dict:
    return {
        "id": e.id,
        "epoch_datetime": e.epoch_datetime.isoformat() if e.epoch_datetime else None,
        "inclination_deg": e.inclination_deg,
        "raan_deg": e.raan_deg,
        "eccentricity": e.eccentricity,
        "arg_of_perigee_deg": e.arg_of_perigee_deg,
        "mean_anomaly_deg": e.mean_anomaly_deg,
        "mean_motion_rev_day": e.mean_motion_rev_day,
        "bstar_drag": e.bstar_drag,
        "rev_number": e.rev_number,
    }


@report_bp.route("/api/satellites/latest-tles", methods=["GET"])
def latest_tles_api():
    """Returns the latest TLE lines for all satellites for proximity matching."""
    subquery = (
        db.session.query(
            TLEElement.satellite_id,
            func.max(TLEElement.id).label("max_id")
        )
        .group_by(TLEElement.satellite_id)
        .subquery()
    )
    
    query = (
        db.session.query(
            Satellite.norad_cat_id, 
            Satellite.name, 
            Satellite.classification,
            Satellite.int_designator,
            TLEElement.raw_line1, 
            TLEElement.raw_line2, 
            TLEElement.mean_motion_rev_day
        )
        .join(TLEElement, Satellite.id == TLEElement.satellite_id)
        .join(subquery, TLEElement.id == subquery.c.max_id)
    )
    
    results = query.all()
    
    data = []
    for r in results:
        data.append({
            "id": r.norad_cat_id,
            "name": r.name,
            "class": r.classification,
            "designator": r.int_designator or "—",
            "l1": r.raw_line1,
            "l2": r.raw_line2,
            "mm": r.mean_motion_rev_day
        })
        
    return jsonify(data)


# ── Geo Query (country bounding-box satellite filter) ───────────────────────

@report_bp.route("/api/geo-query", methods=["POST"])
def geo_query():
    """
    Handles prompts like "Starlink satellites over United States".
    Steps:
      1. Extract country + optional name filter from the prompt.
      2. Pull latest TLEs from the DB.
      3. Propagate each satellite's position in Python.
      4. Return those that fall within the country bounding box.
    """
    from app.services.geo_query_service import resolve_country, extract_name_filter, satellites_over_region, filter_anomalous_altitudes

    user_prompt = request.json.get("prompt", "").strip()
    if not user_prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    # --- 1. Detect country ---
    country_result = resolve_country(user_prompt)
    if not country_result:
        return jsonify({"error": "no_country"}), 404  # caller falls back to LLM

    country_name, bbox = country_result
    name_filter = extract_name_filter(user_prompt)

    # --- 2. Pull latest TLEs ---
    subquery = (
        db.session.query(
            TLEElement.satellite_id,
            func.max(TLEElement.id).label("max_id")
        )
        .group_by(TLEElement.satellite_id)
        .subquery()
    )
    rows = (
        db.session.query(
            Satellite.norad_cat_id,
            Satellite.name,
            Satellite.classification,
            Satellite.int_designator,
            TLEElement.raw_line1,
            TLEElement.raw_line2,
            TLEElement.mean_motion_rev_day,
        )
        .join(TLEElement, Satellite.id == TLEElement.satellite_id)
        .join(subquery, TLEElement.id == subquery.c.max_id)
        .all()
    )

    tles = [
        {
            "id":          r.norad_cat_id,
            "name":        r.name,
            "class":       r.classification,
            "designator":  r.int_designator or "—",
            "l1":          r.raw_line1,
            "l2":          r.raw_line2,
            "mm":          r.mean_motion_rev_day,
        }
        for r in rows
    ]

    # --- 3. Propagate & filter ---
    matched = satellites_over_region(tles, bbox, name_filter=name_filter)
    matched = filter_anomalous_altitudes(matched)

    return jsonify({
        "satellites": [
            {
                "id":          s["id"],
                "name":        s["name"],
                "class":       s["class"],
                "designator":  s["designator"],
                "l1":          s["l1"],
                "l2":          s["l2"],
                "mm":          s["mm"],
                "current_lat": s["current_lat"],
                "current_lon": s["current_lon"],
                "current_alt": s["current_alt"],
            }
            for s in matched
        ],
        "country":      country_name,
        "bbox":         bbox,
        "name_filter":  name_filter,
        "total_scanned": len(tles),
    })


# ── Offline AI Natural Query (Text-to-SQL) ──────────────────────────────────

import os
import re
import time
import logging

log = logging.getLogger(__name__)

_llm_instance = None

def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        from llama_cpp import Llama
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        model_path = os.path.join(models_dir, "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf")
        if not os.path.exists(model_path):
            log.error("[AI Model] Model file not found at path: %s", model_path)
            raise FileNotFoundError("AI model file not found. Please download it first from the Admin panel.")
        
        threads = max(1, min(os.cpu_count() or 4, 8))
        log.info("[AI Model] Lazy-loading GGUF model from %s (threads=%d, n_ctx=2048)...", model_path, threads)
        t0 = time.perf_counter()
        _llm_instance = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=threads,
            verbose=False
        )
        log.info("[AI Model] Model loaded successfully into memory in %.3f seconds.", time.perf_counter() - t0)
    return _llm_instance


def validate_sql_safety(sql: str) -> bool:
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        log.warning("[SQL Guard] Rejected non-SELECT query: %s", sql)
        return False
    # Strict blocklist for any mutation commands
    blocklist = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "PRAGMA", "GRANT", "SHUTDOWN", "ATTACH", "DETACH"]
    for keyword in blocklist:
        if re.search(r'\b' + keyword + r'\b', sql_upper):
            log.warning("[SQL Guard] Rejected query containing blocked keyword '%s': %s", keyword, sql)
            return False
    return True


@report_bp.route("/api/natural-query", methods=["POST"])
def natural_query():
    t_start = time.perf_counter()
    user_prompt = request.json.get("prompt", "").strip() if request.json else ""
    if not user_prompt:
        log.warning("[AI Search] Prompt was empty.")
        return jsonify({"error": "Prompt cannot be empty"}), 400

    log.info("[AI Search] Incoming search request prompt: %r", user_prompt)

    # 0a. Check verified AI Query Cache first (Instant bypass for common recommended queries)
    from app.services.query_cache import get_cached_query, cache_user_verified_query
    
    cached_entry = get_cached_query(user_prompt)
    if cached_entry and not ("-- Geo-query" in cached_entry.get("sql", "")):
        cached_sql = cached_entry["sql"]
        if not validate_sql_safety(cached_sql):
            log.warning("[AI Search] Cached SQL rejected by safety filter for prompt %r.", user_prompt)
            cached_entry = None
        else:
            log.info("[AI Search] Cache HIT for prompt %r. Executing cached SQL: %s", user_prompt, cached_sql)
            t_sql_start = time.perf_counter()
            try:
                raw_results = db.session.execute(db.text(cached_sql)).fetchall()
                norad_ids = []
                for row in raw_results:
                    if hasattr(row, 'norad_cat_id'):
                        norad_ids.append(row.norad_cat_id)
                    elif len(row) > 0:
                        norad_ids.append(row[0])

                norad_ids = [n for n in norad_ids if n is not None]

                if not norad_ids:
                    t_total = time.perf_counter() - t_start
                    return jsonify({
                        "satellites": [],
                        "sql": cached_sql,
                        "cached": True,
                        "perf": {
                            "llm_inference_sec": 0.0,
                            "db_query_sec": round(time.perf_counter() - t_sql_start, 3),
                            "total_time_sec": round(t_total, 3),
                            "mode": "query_cache"
                        }
                    })

                subquery = (
                    db.session.query(TLEElement.satellite_id, func.max(TLEElement.id).label("max_id"))
                    .group_by(TLEElement.satellite_id)
                    .subquery()
                )
                query = (
                    db.session.query(
                        Satellite.norad_cat_id, Satellite.name, Satellite.classification,
                        Satellite.int_designator, TLEElement.raw_line1, TLEElement.raw_line2,
                        TLEElement.mean_motion_rev_day
                    )
                    .join(TLEElement, Satellite.id == TLEElement.satellite_id)
                    .join(subquery, TLEElement.id == subquery.c.max_id)
                    .filter(Satellite.norad_cat_id.in_(norad_ids))
                )
                final_results = query.all()
                t_total = time.perf_counter() - t_start
                data = [{
                    "id": r.norad_cat_id, "name": r.name, "class": r.classification,
                    "designator": r.int_designator or "—", "l1": r.raw_line1, "l2": r.raw_line2,
                    "mm": r.mean_motion_rev_day
                } for r in final_results]

                return jsonify({
                    "satellites": data,
                    "sql": cached_sql,
                    "cached": True,
                    "category": cached_entry.get("category", "cached"),
                    "perf": {
                        "llm_inference_sec": 0.0,
                        "db_query_sec": round(time.perf_counter() - t_sql_start, 3),
                        "total_time_sec": round(t_total, 3),
                        "mode": "query_cache"
                    }
                })
            except Exception as ex:
                log.warning("[AI Search] Cached SQL execution failed for %r: %s. Falling back to LLM.", user_prompt, ex)

    # 0b. Try geo-intent (e.g. "Starlink satellites over United States")
    from app.services.geo_query_service import resolve_country, extract_name_filter, satellites_over_region, filter_anomalous_altitudes

    t_geo_start = time.perf_counter()
    country_result = resolve_country(user_prompt)
    if country_result:
        country_name, bbox = country_result
        name_filter = extract_name_filter(user_prompt)

        subquery = (
            db.session.query(
                TLEElement.satellite_id,
                func.max(TLEElement.id).label("max_id")
            )
            .group_by(TLEElement.satellite_id)
            .subquery()
        )
        rows = (
            db.session.query(
                Satellite.norad_cat_id,
                Satellite.name,
                Satellite.classification,
                Satellite.int_designator,
                TLEElement.raw_line1,
                TLEElement.raw_line2,
                TLEElement.mean_motion_rev_day,
            )
            .join(TLEElement, Satellite.id == TLEElement.satellite_id)
            .join(subquery, TLEElement.id == subquery.c.max_id)
            .all()
        )

        tles = [
            {
                "id":         r.norad_cat_id,
                "name":       r.name,
                "class":      r.classification,
                "designator": r.int_designator or "—",
                "l1":         r.raw_line1,
                "l2":         r.raw_line2,
                "mm":         r.mean_motion_rev_day,
            }
            for r in rows
        ]

        matched = satellites_over_region(tles, bbox, name_filter=name_filter)
        matched = filter_anomalous_altitudes(matched)

        t_geo_dur = time.perf_counter() - t_geo_start
        t_total = time.perf_counter() - t_start
        log.info(
            "[AI Search] Bypassed LLM via Geo-query for '%s' in %.3fs (scanned %d satellites, matched %d).",
            country_name, t_geo_dur, len(tles), len(matched)
        )

        filter_desc = f"WHERE name LIKE '%{name_filter}%' AND " if name_filter else ""
        pseudo_sql = (
            f"-- Geo-query: propagated positions at current UTC time\n"
            f"SELECT norad_cat_id FROM satellites\n"
            f"  {filter_desc}"
            f"  BOUNDING BOX lat=[{bbox[0]}, {bbox[1]}] lon=[{bbox[2]}, {bbox[3]}]  -- {country_name}\n"
            f"  (scanned {len(tles)} satellites, found {len(matched)})"
        )

        return jsonify({
            "satellites": [
                {
                    "id":          s["id"],
                    "name":        s["name"],
                    "class":       s["class"],
                    "designator":  s["designator"],
                    "l1":          s["l1"],
                    "l2":          s["l2"],
                    "mm":          s["mm"],
                    "current_lat": s.get("current_lat"),
                    "current_lon": s.get("current_lon"),
                    "current_alt": s.get("current_alt"),
                }
                for s in matched
            ],
            "sql": pseudo_sql,
            "geo": {
                "country":      country_name,
                "bbox":         bbox,
                "name_filter":  name_filter,
                "total_scanned": len(tles),
            },
            "perf": {
                "llm_inference_sec": 0.0,
                "db_query_sec": round(t_geo_dur, 3),
                "total_time_sec": round(t_total, 3),
                "mode": "geo_bypass"
            }
        })

    # 1. Ensure model is loaded
    try:
        t_model_start = time.perf_counter()
        llm = _get_llm()
        t_model_dur = time.perf_counter() - t_model_start
        log.debug("[AI Search] Model handle ready in %.4fs", t_model_dur)
    except FileNotFoundError as e:
        log.warning("[AI Search] AI model file missing: %s", e)
        return jsonify({"error": "AI model not available. Please download it from the Admin panel."}), 404
    except Exception as e:
        log.exception("[AI Search] Error initializing AI model")
        return jsonify({"error": "Failed to load the AI model."}), 500

    # 2. Formulate system prompt for Qwen2.5-Coder
    system_prompt = (
        "You are a Text-to-SQL translator for a SQLite database.\n"
        "Tables:\n"
        "1. satellites:\n"
        "   - id (INTEGER, PK)\n"
        "   - norad_cat_id (INTEGER, Unique)\n"
        "   - name (VARCHAR)\n"
        "   - classification (VARCHAR)\n"
        "   - int_designator (VARCHAR)\n"
        "2. tle_elements:\n"
        "   - id (INTEGER, PK)\n"
        "   - satellite_id (INTEGER, FK to satellites.id)\n"
        "   - epoch_datetime (DATETIME)\n"
        "   - inclination_deg (FLOAT)\n"
        "   - eccentricity (FLOAT)\n"
        "   - mean_motion_rev_day (FLOAT)\n\n"
        "Rules:\n"
        "- Translate user's query into a valid SQLite SELECT query.\n"
        "- Return ONLY the SQLite SELECT query. Do NOT include markdown code blocks (```sql) or explanations.\n"
        "- Your query MUST select the 'norad_cat_id' column from the satellites table (e.g. SELECT s.norad_cat_id FROM satellites s ...).\n"
        "- If querying epoch parameters like inclination_deg, eccentricity, or mean_motion_rev_day, you MUST JOIN tle_elements (e.g. JOIN tle_elements t ON s.id = t.satellite_id).\n"
        "- Limit the query to 50 results if not specified.\n\n"
        "Examples:\n"
        "Request: Show me Starlink satellites with inclination greater than 53\n"
        "Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id WHERE s.name LIKE '%STARLINK%' AND t.inclination_deg > 53 LIMIT 50;\n\n"
        "Request: Find satellites with mean motion greater than 15\n"
        "Query: SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id WHERE t.mean_motion_rev_day > 15 LIMIT 50;"
    )

    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"

    try:
        log.info("[AI Search] Starting LLM SQL inference generation...")
        t_llm_start = time.perf_counter()
        response = llm(
            prompt,
            max_tokens=128,
            stop=["<|im_end|>"],
            temperature=0.1
        )
        t_llm_dur = time.perf_counter() - t_llm_start
        generated_sql = response["choices"][0]["text"].strip()
        usage = response.get("usage", {})
        log.info(
            "[AI Search] LLM inference completed in %.3fs (prompt_tokens=%s, completion_tokens=%s, total_tokens=%s). Generated SQL: %s",
            t_llm_dur,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
            generated_sql
        )

        full_llm_response = response

        # Clean any backticks or formatting
        if "```" in generated_sql:
            matches = re.findall(r"```(?:sql)?\s*(.*?)\s*```", generated_sql, re.DOTALL)
            if matches:
                generated_sql = matches[0].strip()
            else:
                generated_sql = generated_sql.replace("```", "").strip()

        generated_sql = generated_sql.rstrip(";") + ";"

        # 3. Security check
        if not validate_sql_safety(generated_sql):
            log.warning("[AI Search] Blocked unsafe SQL query: %s", generated_sql)
            return jsonify({
                "error": "Query blocked for security safety.",
                "sql": generated_sql
            }), 400

        # 4. Execute query to retrieve NORAD catalog IDs
        t_sql_start = time.perf_counter()
        raw_results = db.session.execute(db.text(generated_sql)).fetchall()
        
        norad_ids = []
        for row in raw_results:
            if hasattr(row, 'norad_cat_id'):
                norad_ids.append(row.norad_cat_id)
            elif len(row) > 0:
                norad_ids.append(row[0])

        if not norad_ids:
            t_total = time.perf_counter() - t_start
            log.info("[AI Search] Query returned 0 results. Executed in %.3fs (total API time: %.3fs).", time.perf_counter() - t_sql_start, t_total)
            return jsonify({
                "satellites": [],
                "sql": generated_sql,
                "perf": {
                    "llm_inference_sec": round(t_llm_dur, 3),
                    "db_query_sec": round(time.perf_counter() - t_sql_start, 3),
                    "total_time_sec": round(t_total, 3),
                    "mode": "offline_llm"
                }
            })

        # 5. Fetch full satellite data including TLE elements
        subquery = (
            db.session.query(TLEElement.satellite_id, func.max(TLEElement.id).label("max_id"))
            .group_by(TLEElement.satellite_id)
            .subquery()
        )
        
        query = (
            db.session.query(
                Satellite.norad_cat_id, 
                Satellite.name, 
                Satellite.classification,
                Satellite.int_designator,
                TLEElement.raw_line1, 
                TLEElement.raw_line2, 
                TLEElement.mean_motion_rev_day
            )
            .join(TLEElement, Satellite.id == TLEElement.satellite_id)
            .join(subquery, TLEElement.id == subquery.c.max_id)
            .filter(Satellite.norad_cat_id.in_(norad_ids))
        )
        
        final_results = query.all()
        t_sql_dur = time.perf_counter() - t_sql_start
        t_total = time.perf_counter() - t_start

        data = []
        for r in final_results:
            data.append({
                "id": r.norad_cat_id,
                "name": r.name,
                "class": r.classification,
                "designator": r.int_designator or "—",
                "l1": r.raw_line1,
                "l2": r.raw_line2,
                "mm": r.mean_motion_rev_day
            })

        log.info(
            "[AI Search] Successfully returned %d satellites. DB query time: %.3fs | Total API time: %.3fs",
            len(data), t_sql_dur, t_total
        )

        return jsonify({
            "satellites": data,
            "sql": generated_sql,
            "llm_raw_response": {
                "model": full_llm_response.get("model", "unknown"),
                "usage": full_llm_response.get("usage", {}),
                "raw_text": generated_sql,
                "full_raw_text": full_llm_response.get("choices", [{}])[0].get("text", ""),
                "finish_reason": full_llm_response.get("choices", [{}])[0].get("finish_reason", ""),
            },
            "perf": {
                "llm_inference_sec": round(t_llm_dur, 3),
                "db_query_sec": round(t_sql_dur, 3),
                "total_time_sec": round(t_total, 3),
                "mode": "offline_llm"
            }
        })

    except Exception as e:
        log.exception("[AI Search] Internal execution error processing prompt %r", user_prompt)
        return jsonify({"error": "Execution error while processing your request."}), 500


@report_bp.route("/api/ai/cache-feedback", methods=["POST"])
@admin_required
def cache_feedback():
    """Receive user feedback on an AI query and cache verified SQL to data/ai_query_cache.json."""
    data = request.json or {}
    prompt = data.get("prompt", "").strip()
    sql = data.get("sql", "").strip()
    feedback = data.get("feedback", "").strip().lower()

    if not prompt or not sql:
        return jsonify({"error": "Prompt and SQL are required"}), 400

    if feedback in ("positive", "verify", "cache"):
        from app.services.query_cache import cache_user_verified_query
        try:
            entry = cache_user_verified_query(prompt, sql, category="user_verified")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        log.info("[AI Search] User verified query saved to data/ai_query_cache.json: %r", prompt)
        return jsonify({
            "status": "success",
            "message": "Query verified and cached to data/ai_query_cache.json!",
            "entry": entry
        })
    else:
        log.info("[AI Search] User reported negative feedback for prompt %r", prompt)
        return jsonify({"status": "acknowledged", "message": "Feedback recorded."})


@report_bp.route("/api/ai/cached-queries", methods=["GET"])
@admin_required
def cached_queries_api():
    """Return list of cached query examples."""
    from app.services.query_cache import load_query_cache
    queries = load_query_cache()
    return jsonify({"queries": queries})

