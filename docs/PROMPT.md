# 🚀 One-Shot Project Generation Prompt: Satellite TLE Tracker & AI Orbital Discovery

Use the following complete, self-contained prompt to generate or recreate this entire production-ready Flask application from scratch using any advanced coding LLM or AI agent.

---

```markdown
You are an expert full-stack developer, software architect, and aerospace software engineer. Your task is to build a complete, production-ready Flask web application for satellite Two-Line Element (TLE) data management, real-time SGP4 orbital propagation, 2D/3D map tracking, geo-spatial country proximity filtering, and offline AI Text-to-SQL search.

## 🛠️ Technology Stack Requirements
1. **Backend Framework**: Python 3.9+ with Flask 3.0+. Use Flask Blueprints to organize routes (`setup`, `upload`, `report`, `tracker`, `admin`, `auth`).
2. **Database & ORM**: SQLAlchemy 2.0+ with **selectable SQLite or PostgreSQL** (`psycopg[binary]`, URI `postgresql+psycopg://`). Engine choice lives in `instance/datastore.json` (not in the satellite tables). First launch shows `/setup`; Admin can switch later with optional row copy. Compose pins `postgres:18.6-alpine`.
3. **Orbital Mechanics**: `sgp4` (v2.20+) Python package for computing satellite ECI position vector (x, y, z) and velocity vector (vx, vy, vz) converted to geodetic latitude, longitude, and altitude.
4. **Offline AI Natural Language Search**: In-process Text-to-SQL generation using `llama-cpp-python` with quantized GGUF models (`Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf`). Must execute 100% offline without external cloud APIs.
5. **Security**: Read-only SQL validators blocking non-`SELECT` statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `PRAGMA`). Admin SQL console allows only a single `SELECT` / `WITH` / `EXPLAIN`. Google OAuth 2.0 via Authlib. `is_local_dev()` must return **false** when `FLASK_ENV=production` and must **not** treat `RUNNING_IN_DOCKER` as local.
6. **Frontend & Map Engine**: Vanilla HTML5/CSS (cyber dark mode), Leaflet.js 1.9+, `satellite.js`. Default basemap is **Esri World Dark Gray** (no API key). Optional `CARTO_API_KEY` enables CARTO `dark_all`. Maps support CSS fullscreen pop-out and Escape to return.

---

## 🗄️ Database Schema Specification

### 1. `satellites` Table
- `norad_cat_id` (Integer, Primary Key): Unique NORAD catalog catalog identifier (e.g. 25544 for ISS).
- `name` (String 255, Indexed, Not Null): Satellite name.
- `classification_type` (String 1, Default 'U'): Security classification ('U' = Unclassified).
- `intl_designator` (String 50): COSPAR international designator (e.g. '1998-067A').
- `created_at` (DateTime): UTC timestamp of initial ingestion.
- `updated_at` (DateTime): UTC timestamp of last TLE update.

### 2. `tle_elements` Table
- `id` (Integer, Primary Key, Autoincrement)
- `satellite_id` (Integer, ForeignKey `satellites.norad_cat_id`, Not Null, Indexed)
- `epoch_datetime` (DateTime, Not Null, Indexed): Calculated UTC epoch timestamp of the TLE record.
- `element_set_no` (Integer): Element set number.
- `ephemeris_type` (Integer, Default 0)
- `inclination_deg` (Float, Not Null): Orbital inclination in degrees [0° - 180°].
- `raan_deg` (Float, Not Null): Right Ascension of Ascending Node in degrees [0° - 360°].
- `eccentricity` (Float, Not Null): Orbital eccentricity [0.0 - 1.0].
- `arg_of_perigee_deg` (Float, Not Null): Argument of Perigee in degrees [0° - 360°].
- `mean_anomaly_deg` (Float, Not Null): Mean Anomaly in degrees [0° - 360°].
- `mean_motion_rev_day` (Float, Not Null): Mean Motion in revolutions per day.
- `rev_at_epoch` (Integer): Revolution number at epoch.
- `bstar_drag` (Float): BSTAR drag term coefficient.
- `first_derivative_mean_motion` (Float): Ballistic coefficient first derivative.
- `second_derivative_mean_motion` (Float): Ballistic coefficient second derivative.
- `raw_line1` (Text, Not Null): Original Line 1 string of the TLE.
- `raw_line2` (Text, Not Null): Original Line 2 string of the TLE.
- **Unique Constraint**: `(satellite_id, epoch_datetime)` to prevent duplicate ingestion of identical epoch records.

### 3. `upload_sessions` Table
- `id` (Integer, Primary Key, Autoincrement)
- `filename` (String 255): Name of the uploaded file or seed dataset label.
- `uploaded_at` (DateTime): UTC upload timestamp.
- `records_processed` (Integer): Total 3-line sets parsed.
- `satellites_added` (Integer): Count of new satellite catalog entries created.
- `satellites_updated` (Integer): Count of existing satellites updated.
- `duplicates_skipped` (Integer): Count of identical epoch TLE records skipped.

### 4. `system_settings` Table
- `key` (String 100, Primary Key)
- `value` (Text)
- `updated_at` (DateTime)

### 5. `saved_queries` Table
Admin SQL editor bookmarks stored in the **active** datastore (survive restarts and migrate with engine switch).
- `id`, `name`, `sql`, `row_limit`, `created_at`
- `last_run_at`, `last_run_ms`, `last_run_row_count`, `run_count`
- `latency_p50_ms`, `latency_p95_ms`, `latency_p99_ms`, `latency_p100_ms`, `latency_samples_json` (cap 200 samples)

---

## 💻 Core Application Modules & Functional Requirements

### 1. Ingestion Engine & Deduplication (`app/services/parser.py`)
- Parse standard 3-line TLE files (`.txt`, `.tle`, `.dat`). Line 0 = Satellite Name, Line 1 = TLE Line 1 (starts with `1 `), Line 2 = TLE Line 2 (starts with `2 `).
- Calculate UTC Epoch from Line 1 fields (2-digit epoch year + fractional day of year).
- Compute Keplerian orbital elements from Line 1 & Line 2 formatted columns.
- Implement atomic transaction deduplication: match existing satellites by `norad_cat_id`. Skip inserting `tle_elements` if `(satellite_id, epoch_datetime)` already exists in DB.

### 2. SGP4 Propagation & Country Proximity Filter (`app/services/geo_query_service.py`)
- Load satellite TLE strings into `sgp4.api.Satrec.twoline2rv`.
- Propagate orbit to specified UTC datetime (current time by default) to return ECI position $(x, y, z)$ in kilometers.
- Convert ECI position to Greenwich Hour Angle (GHA) and calculate geodetic Latitude, Longitude, and Altitude above Earth ellipsoid.
- Country dropdown lists only countries that have both bounding-box and center data (`GET /api/proximity/options`).
- Prefix table: first word of each satellite name (`CSS (TIANHE)` → `CSS`, `STARLINK-1007` → `STARLINK`).
- **Keyword Search** (default Search tab): empty `q` lists all rows; non-empty `q` `ILIKE`s name, NORAD ID, designator, classification, and raw TLE lines.

### 3. Offline AI Text-to-SQL Search (`app/services/llm_search.py`)
- Download and load quantized GGUF model `Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf` using `llama-cpp-python`.
- Prompt construction: provide SQLite table schema (`satellites`, `tle_elements`) and system instructions to return **ONLY** executable SQL inside ````sql ... ```` blocks.
- **SQL Security Guardrail**: Enforce strict validation via regex/AST parsing. Reject any query containing non-`SELECT` commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `ATTACH`, `PRAGMA`). Return user-friendly validation error if unsafe query is generated.
- Track execution telemetry: breakdown timing into `Total Execution Time`, `LLM Inference Time`, and `Database Query Time`.

### 4. 2D Map & 3D Globe Interactive Tracker (`app/templates/tracker.html` & `app/static/js/tracker.js`)
- Render 2D map using Leaflet.js via `app/static/js/basemap.js` (Esri default; CARTO if `CARTO_API_KEY`).
- Dynamically project orbit paths, ground tracks, sub-satellite points, and coverage footprints for selected satellites using `satellite.js`.
- Telemetry sidebar displaying live updating values: Latitude, Longitude, Altitude (km), Velocity (km/s), Azimuth, Elevation, and TLE Keplerian parameters.
- Full screen / Exit full screen (and Escape) on satellite detail `#orbit-map-card` and tracker `#tracker-map-shell`; call Leaflet `invalidateSize` after toggle.
- Optional tracker overlays (off by default), free sources only, attributed on the map: **Weather & quakes** (NASA EONET weather/climate plus USGS earthquakes; quake bubbles scale size and color by magnitude; Open-Meteo ERA5 daily means for cities over 1 million with 7d / 30d / 90d / 1y °C change), **Markets** (CNBC levels + 1d %; 7d / 30d / 1q / 6m / 1y / 2y / 5y / 10y % from Yahoo daily closes), **Currencies** (Frankfurter FX/gold, CNBC WTI, The Economist Big Mac Index; local units to buy 1 USD/EUR/yen/oz gold/barrel/Big Mac plus 1d / 7d / 30d / 90d / 6m / 1y / 5y %), **Flights** (OpenSky positions; adsbdb origin/destination; estimated on-time), **News** (last 24h: GDACS plus UN News, Global Voices CC BY 3.0, The Conversation CC BY-ND, Deutsche Welle RSS; gazetteer pins; title opens the article), **Ships** (Fintraffic Digitraffic AIS current position, CC BY 4.0, Finland/Baltic), **Webcams** (official worldwide pages plus OpenStreetMap webcam URLs via Overpass; tooltip title opens the feed in a new tab), **Cloud DCs** (AWS / Azure / GCP region pins; tooltip HTTPS ping p50 / p95 / p99 from this server).

### 5. Admin Panel, Datastore, SQL Explorer & Dev Bypass
- First-launch `/setup` (`app/routes/setup.py`) writes `instance/datastore.json`. Headless bootstrap via `DATABASE_URL` or `DB_ENGINE`.
- If `data/kaggle_tle_data.txt` is missing, seed bundled demo TLEs marked `source=demo` (`app/services/demo_tle.py`). `ensure_database_schema()` before routes that query `uploads`.
- Dashboard: database stats, datastore switch form, link to **Tables & SQL editor**.
- `/admin/database`: table counts, read-only SQL, row cap, CSV/Excel export, saved queries with latency percentiles.
- Google OAuth 2.0. `is_local_dev()` is false in production; Docker alone must not enable `/auth/dev-bypass`.
- Compose: `user: ${SATTRACK_UID:-1000}:${SATTRACK_GID:-1000}` so `instance/` is not root-owned mode 600.

---

## 🎨 UI/UX & CSS Design System (`app/static/css/style.css` & `report.css`)
- **Theme**: Futuristic Cyber Dark Mode.
- **Background**: Deep space obsidian `#070a12` with gradient overlays.
- **Card Surfaces**: Translucent glassmorphism `#0d1526` with 1px border `rgba(255, 255, 255, 0.08)` and subtle cyan box shadows `0 0 20px rgba(6, 182, 212, 0.1)`.
- **Accent Glow**: Neon cyan `#38bdf8`, electric blue `#3b82f6`, and violet `#a78bfa`.
- **Typography**: Inter / system sans-serif for UI text, JetBrains Mono / Fira Code for NORAD IDs, SQL queries, TLE lines, and performance metrics.
- **Responsive Layout**: Flexbox and CSS Grid adapt smoothly across mobile, tablet, and widescreen desktop devices.

---

## 📁 Repository Directory Blueprint
```
satellite-tracker/
├── app/
│   ├── __init__.py          # Flask application factory, DB & OAuth setup
│   ├── models.py            # SQLAlchemy models (Satellite, TLEElement, etc.)
│   ├── routes/
│   │   ├── admin.py         # Admin dashboard, datastore switch, SQL explorer
│   │   ├── auth.py          # Google OAuth2 & fail-closed local bypass
│   │   ├── report.py        # Keyword, proximity, AI query, tracker routes
│   │   ├── setup.py         # First-launch SQLite / PostgreSQL wizard
│   │   └── upload.py        # GET form + POST ingest
│   ├── services/
│   │   ├── datastore.py     # URI build, schema ensure, snapshot migrate
│   │   ├── demo_tle.py      # Bundled demo TLE seed
│   │   ├── sql_console.py   # Read-only SQL, saved queries, latency
│   │   ├── geo_query_service.py
│   │   └── tle_parser.py
│   ├── static/
│   │   ├── css/
│   │   │   ├── report.css
│   │   │   ├── style.css
│   │   │   └── tracker.css
│   │   └── js/
│   │       ├── basemap.js   # Esri default / optional CARTO
│   │       ├── datastore.js
│   │       └── tracker.js
│   └── templates/
│       ├── admin.html
│       ├── admin_database.html
│       ├── setup.html
│       ├── report.html      # Keyword default, country + prefix table, AI
│       ├── satellite_detail.html
│       ├── tracker.html
│       └── upload.html
├── docker-compose.yml       # App + postgres:18.6-alpine + test profiles
├── config.py
├── run.py
├── Dockerfile               # FLASK_ENV=production (no Docker-as-local bypass)
├── requirements.txt
└── README.md
```
```
