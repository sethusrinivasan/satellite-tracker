# 🚀 One-Shot Project Generation Prompt: Satellite TLE Tracker & AI Orbital Discovery

Use the following complete, self-contained prompt to generate or recreate this entire production-ready Flask application from scratch using any advanced coding LLM or AI agent.

---

```markdown
You are an expert full-stack developer, software architect, and aerospace software engineer. Your task is to build a complete, production-ready Flask web application for satellite Two-Line Element (TLE) data management, real-time SGP4 orbital propagation, 2D/3D map tracking, geo-spatial country proximity filtering, and offline AI Text-to-SQL search.

## 🛠️ Technology Stack Requirements
1. **Backend Framework**: Python 3.9+ with Flask 3.0+. Use Flask Blueprints to organize routes (`upload`, `report`, `tracker`, `admin`, `auth`).
2. **Database & ORM**: SQLite database with SQLAlchemy 2.0+. Enforce relational schema constraints, unique indices, and deduplication logic.
3. **Orbital Mechanics**: `sgp4` (v2.20+) Python package for computing satellite ECI position vector (x, y, z) and velocity vector (vx, vy, vz) converted to geodetic latitude, longitude, and altitude.
4. **Offline AI Natural Language Search**: In-process Text-to-SQL generation using `llama-cpp-python` with quantized GGUF models (`Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf`). Must execute 100% offline without external cloud APIs.
5. **Security**: Read-only AST/regex SQL validator blocking non-`SELECT` statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `PRAGMA`). Google OAuth 2.0 authentication via Authlib with an environment-gated local development bypass for testing.
6. **Frontend & Map Engine**: Vanilla HTML5, modern Vanilla CSS (cyber dark mode with glassmorphism and cyan `#38bdf8` glow design system), Leaflet.js 1.9+, and `satellite.js` for client-side orbit path calculation.

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

---

## 💻 Core Application Modules & Functional Requirements

### 1. Ingestion Engine & Deduplication (`app/services/parser.py`)
- Parse standard 3-line TLE files (`.txt`, `.tle`, `.dat`). Line 0 = Satellite Name, Line 1 = TLE Line 1 (starts with `1 `), Line 2 = TLE Line 2 (starts with `2 `).
- Calculate UTC Epoch from Line 1 fields (2-digit epoch year + fractional day of year).
- Compute Keplerian orbital elements from Line 1 & Line 2 formatted columns.
- Implement atomic transaction deduplication: match existing satellites by `norad_cat_id`. Skip inserting `tle_elements` if `(satellite_id, epoch_datetime)` already exists in DB.

### 2. SGP4 Propagation & Country Proximity Filter (`app/services/sgp4_service.py`)
- Load satellite TLE strings into `sgp4.api.Satrec.twoline2rv`.
- Propagate orbit to specified UTC datetime (current time by default) to return ECI position $(x, y, z)$ in kilometers.
- Convert ECI position to Greenwich Hour Angle (GHA) and calculate geodetic Latitude, Longitude, and Altitude above Earth ellipsoid.
- Provide country bounding-box lookup (e.g. United States, India, Germany, United Kingdom, Japan) to filter satellites currently overhead.

### 3. Offline AI Text-to-SQL Search (`app/services/llm_search.py`)
- Download and load quantized GGUF model `Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf` using `llama-cpp-python`.
- Prompt construction: provide SQLite table schema (`satellites`, `tle_elements`) and system instructions to return **ONLY** executable SQL inside ````sql ... ```` blocks.
- **SQL Security Guardrail**: Enforce strict validation via regex/AST parsing. Reject any query containing non-`SELECT` commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `ATTACH`, `PRAGMA`). Return user-friendly validation error if unsafe query is generated.
- Track execution telemetry: breakdown timing into `Total Execution Time`, `LLM Inference Time`, and `Database Query Time`.

### 4. 2D Map & 3D Globe Interactive Tracker (`app/templates/tracker.html` & `app/static/js/tracker.js`)
- Render 2D map using Leaflet.js with dark-mode satellite tiles.
- Dynamically project orbit paths, ground tracks, sub-satellite points, and coverage footprints for selected satellites using `satellite.js`.
- Telemetry sidebar displaying live updating values: Latitude, Longitude, Altitude (km), Velocity (km/s), Azimuth, Elevation, and TLE Keplerian parameters.

### 5. Admin Panel & Dev Bypass (`app/routes/admin.py` & `app/routes/auth.py`)
- Dashboard displaying database stats (Total Satellites, TLE Records, Upload Sessions, Kaggle Seed status).
- System Resource Telemetry Gauges (`CPU Load %`, `RAM Usage %`, `Disk Storage %`) computed via `psutil`.
- Upload Session History table with one-click session deletion and full database reset triggers.
- GGUF model downloader manager with real-time download progress reporting.
- Google OAuth 2.0 authentication flow with local development mode auto-detection (`is_local_dev()`) providing an optional one-click **Local Dev Admin Bypass** button when OAuth keys are unconfigured.

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
│   │   ├── admin.py         # Admin dashboard, resets, model manager
│   │   ├── auth.py          # Google OAuth2 & dev bypass route
│   │   ├── main.py          # Index & static landing routes
│   │   ├── report.py        # Search, country filter, AI query routes
│   │   └── upload.py        # File ingestion & deduplication routes
│   ├── services/
│   │   ├── llm_search.py    # llama-cpp-python Text-to-SQL & SQL safety check
│   │   ├── parser.py        # 3-line TLE file parser & epoch calculation
│   │   └── sgp4_service.py  # SGP4 orbit propagation & position calculations
│   ├── static/
│   │   ├── css/
│   │   │   ├── report.css   # AI search & metrics styling
│   │   │   ├── style.css    # Global cyber design system & tokens
│   │   │   └── tracker.css  # Leaflet map & telemetry sidebar styles
│   │   └── js/
│   │       └── tracker.js   # Real-time Leaflet & satellite.js tracking logic
│   └── templates/
│       ├── admin.html       # Admin control center & resource gauges
│       ├── auth_error.html  # OAuth error page with local dev bypass button
│       ├── base.html        # Main Jinja2 layout header/footer structure
│       ├── index.html       # Landing page with feature showcases
│       ├── report.html      # Search, country proximity & AI search tab UI
│       ├── tracker.html     # Live 2D/3D orbital tracker interface
│       └── upload.html      # TLE dropzone & ingestion audit grid
├── config.py                # Environment configuration settings
├── run.py                   # Application entry point script
├── Dockerfile               # Container build instructions
├── requirements.txt         # Python dependencies
└── README.md                # Documentation & quickstart guide
```
```
