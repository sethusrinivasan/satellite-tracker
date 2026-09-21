# 📌 Known Issues, Auditing & TODO Roadmap

This document tracks known issues, technical limitations, security guardrails, and planned enhancement items for the **Satellite TLE Tracker & AI Orbital Discovery** platform.

All issue items generated during system audits are tagged with `Antigravity_generated` for automated issue tracking on **[GitHub Issues](https://github.com/sethusrinivasan/satellite-tracker/issues)**.

---

## 🏷️ Issue Prioritization Matrix

| Priority Level | Classification | Impact & Scope | Target Timeline |
| :--- | :--- | :--- | :--- |
| 🔴 **P0 (Critical)** | Security & Data Safety | SQL injection risks, safety bypass, data corruption | Immediate / Hotfix |
| 🟠 **P1 (High)** | Core Functionality & Latency | LLM inference delays, JOIN accuracy edge cases | Next Minor Release |
| 🟡 **P2 (Medium)** | Scalability & Admin UX | Pure-Python SGP4 CPU bottleneck, Admin UI config | Planned Backlog |
| 🟢 **P3 (Low)** | Enhancements & Extensibility | 3D WebGL visual upgrades, TimescaleDB time-series | Future Exploration |

---

## 🐛 Known Issues & Audit Items

### 1. 🔴 [P0] SQL Mutation Blocklist & Query Guardrails
- **Summary**: Ensure Text-to-SQL generated queries cannot execute mutating SQL statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `ATTACH`, `PRAGMA`).
- **Status**: Implemented via regex blocklist validation in `app/routes/report.py`. Admin SQL console (`sql_console.validate_readonly_sql`) additionally rejects stacked statements and allows only `SELECT` / `WITH` / `EXPLAIN`.
- **Labels / Tags**: `Antigravity_generated`, `security`, `p0`
- **Tracking**: [Issue #1: Validate SQL Safety Filter](https://github.com/sethusrinivasan/satellite-tracker/issues/1)

### 2. 🔴 [P0] Docker treated as local admin bypass — **fixed**
- **Summary**: `is_local_dev()` previously treated `RUNNING_IN_DOCKER` as local, which exposed `/auth/dev-bypass` on advertised 1-click and Compose images with `FLASK_ENV=production`.
- **Status**: `FLASK_ENV=production` short-circuits to false. Host must be `localhost` / `127.0.0.1` or an explicit development env. Docker is not sufficient.
- **Labels / Tags**: `security`, `p0`

### 3. 🟠 [P1] Compact LLM Multi-Table JOIN Edge Cases
- **Summary**: The 1.5B quantized GGUF model (`Qwen2.5-Coder-1.5B-Instruct-Q4_K_M`) accurately translates standard queries into SQL, but may occasionally omit `JOIN tle_elements` on complex prompts referencing orbital parameters.
- **Workaround**: System prompt few-shot examples guide the model toward proper `JOIN` syntax.
- **Labels / Tags**: `Antigravity_generated`, `ai`, `p1`
- **Tracking**: [Issue #2: Improve LLM SQL JOIN reasoning for complex multi-table queries](https://github.com/sethusrinivasan/satellite-tracker/issues/2)

### 4. 🟠 [P1] Local LLM Inference Latency & UI System Load Feedback
- **Summary**: Local CPU GGUF inference on single/dual-core machines can take 5–15 seconds per natural language query.
- **Status**: Implemented real-time UI system load indicator (`⚙️ Processing prompt... High CPU load expected`) and performance timing breakdown (`⚡ System Performance: Total X.Xs`).
- **Labels / Tags**: `Antigravity_generated`, `performance`, `p1`
- **Tracking**: [Issue #3: Local GGUF Model Inference Latency & System Load Reporting](https://github.com/sethusrinivasan/satellite-tracker/issues/3)

### 5. 🟠 [P1] Live AI SQL validator vs cache validator
- **Summary**: Cached AI SQL rejects `;` entirely. The live Text-to-SQL path is historically more permissive about statement separators. Prefer the admin SQL console rules (`validate_readonly_sql`) if tightening the live path.
- **Status**: Open hardening item. Admin `/admin/database` already blocks stacked statements.
- **Labels / Tags**: `security`, `p1`

### 6. 🟡 [P2] High-Density SGP4 Propagation CPU Optimization
- **Summary**: SGP4 orbit propagation for country proximity search is computed in pure Python (`geo_query_service.py`) and also in the browser via `satellite.js`. Scanning >20,000 active TLE records can take 1–2 seconds.
- **Mitigation**: Anomalous/decaying orbits are filtered out and LEO altitude bands are prioritized. Prefix filter reduces the client-side set.
- **Labels / Tags**: `Antigravity_generated`, `performance`, `p2`
- **Tracking**: [Issue #4: Optimize Python SGP4 propagation with C-extensions / Numba batching](https://github.com/sethusrinivasan/satellite-tracker/issues/4)

### 7. 🟡 [P2] CARTO dark tiles require an API key — **mitigated**
- **Summary**: Unauthenticated CARTO `dark_all` tiles watermark **API KEY REQUIRED**.
- **Status**: Default basemap is Esri World Dark Gray (`app/static/js/basemap.js`). Set `CARTO_API_KEY` (free CARTO basemap key) to restore CARTO tiles.

### 8. 🟡 [P2] Overlay provider gaps
- **Summary**: Some free overlay feeds are incomplete or delayed. Open-Meteo city temperatures use ERA5 daily means and can lag a few days. Currency oil and Big Mac rows have no multi-horizon %. A few market indexes have no Yahoo daily series (those pins keep CNBC 1d only, or use a named ETF proxy). Flight on-time is estimated, not an airline schedule. Live AIS is Finland/Baltic only. OSM extra webcams can be empty at world zoom if Overpass is slow. Cloud DC pins are city-level; latency is HTTPS RTT from this server (not ICMP, not the viewer’s browser). Some Azure Speed Test blobs may be missing. Overlay HTTP backs off a host after `429`/`503` and keeps serving stale or partial pins.
- **Status**: Live overlays work with the documented free sources. Follow-ups: richer geo-news, tourist/Wikipedia-edit overlays, denser global webcams.
- **Labels / Tags**: `overlay`, `p2`

### 9. 🟡 [P2] `instance/datastore.json` Permission denied — **mitigated**
- **Summary**: Compose running as root wrote `datastore.json` mode `600` as `root:root`. Host `./run.sh --local` then logged `Permission denied` and treated the app as unconfigured (`/setup` loop).
- **Status**: Compose `user: ${SATTRACK_UID}:${SATTRACK_GID}`; `run.sh` exports those IDs; root processes repair ownership; `PermissionError` is logged once with a chown hint and marked `DATASTORE_UNREADABLE`.

---

## 🗺️ TODO Roadmap & Feature Backlog

- [x] 🟢 **[P3] PostgreSQL driver support**: SQLite and PostgreSQL are selectable on first launch and from Admin → Database. Compose pins `postgres:18.6-alpine`. (`database`)
- [ ] 🟡 **[P2] Overlay follow-ups**: denser geo-news, tourist destinations, Wikipedia geolocated edits, and more OSM/official webcams outside hub cities. (`overlay`, `p2`)
- [ ] 🟢 **[P3] Enhanced 3D WebGL Globe View**: Upgrade 2D/3D tracking interface with CesiumJS / Three.js for realistic Earth textures and orbital trajectory rendering. (`Antigravity_generated`, `frontend`, `p3`) ([Issue #6](https://github.com/sethusrinivasan/satellite-tracker/issues/6))
- [ ] 🟢 **[P3] TimescaleDB hypertables**: Optional time-series backend for historical TLE epochs beyond plain PostgreSQL. (`Antigravity_generated`, `database`, `p3`) ([Issue #7](https://github.com/sethusrinivasan/satellite-tracker/issues/7))

---

## 💬 Submitting Issues

When submitting new issues or reporting bugs:
1. Include the `Antigravity_generated` tag if generated during automated audits.
2. Use the provided [Bug Report Template](https://github.com/sethusrinivasan/satellite-tracker/issues/new?template=bug_report.md) or [Feature Request Template](https://github.com/sethusrinivasan/satellite-tracker/issues/new?template=feature_request.md).
