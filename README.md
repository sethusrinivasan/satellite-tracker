# 🛰️ Satellite TLE Tracker & AI Orbital Discovery

[![GitHub Pages Website](https://img.shields.io/badge/Website-GitHub_Pages-22C55E?style=flat-square&logo=github&logoColor=white)](https://sethusrinivasan.github.io/satellite-tracker/)
[![GitHub Repository](https://img.shields.io/badge/GitHub-sethusrinivasan%2Fsatellite--tracker-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/sethusrinivasan/satellite-tracker)
[![CI](https://github.com/sethusrinivasan/satellite-tracker/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/sethusrinivasan/satellite-tracker/actions/workflows/docker-publish.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![One-Shot Prompt](https://img.shields.io/badge/AI_Prompt-One--Shot_Spec-7C3AED?style=flat-square&logo=openai&logoColor=white)](PROMPT.md)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-SQLAlchemy-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18.6-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Offline AI](https://img.shields.io/badge/Offline_AI-llama--cpp--python-FF6F00?style=flat-square&logo=huggingface&logoColor=white)](https://github.com/abetlen/llama-cpp-python)
[![SBOM](https://img.shields.io/badge/SBOM-CycloneDX_v1.5-blue?style=flat-square&logo=json)](sbom.json)

🌐 **Official Site & Docs**: [https://sethusrinivasan.github.io/satellite-tracker/](https://sethusrinivasan.github.io/satellite-tracker/)  
📁 **GitHub Repository**: [https://github.com/sethusrinivasan/satellite-tracker](https://github.com/sethusrinivasan/satellite-tracker)  
🤖 **One-Shot Project Spec**: [`PROMPT.md`](PROMPT.md)

A demonstration and experimental Flask web application for uploading, parsing, exploring, and tracking satellite [Two-Line Element (TLE)](https://en.wikipedia.org/wiki/Two-line_element_set) data. Features real-time [SGP4 (Simplified General Perturbations 4)](https://en.wikipedia.org/wiki/SGP4) orbit propagation, country proximity filtering, interactive 2D/3D map tracking, and an **in-process offline Text-to-SQL AI natural language search** powered by [Qwen2.5-Coder](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct).

> ℹ️ **Project Status & Disclaimer**: This is a **demo / hobby project for learning only**. Do not use it for real operational work, navigation, or production. No SLAs or accuracy guarantees. Feel free to review, copy, fork, and adapt the code.

> 🤖 **One-Shot Generation Prompt**: You can recreate or generate this complete application using our self-contained prompt document [`PROMPT.md`](PROMPT.md).

---

## 🌟 Key Features

- 🛰️ **3-Line TLE Ingestion & Parsing**: Parses standard [TLE format](https://celestrak.org/columns/v04n03/) records, extracts key [Keplerian orbital elements](https://en.wikipedia.org/wiki/Orbital_elements) ([Inclination](https://en.wikipedia.org/wiki/Orbital_inclination), [Eccentricity](https://en.wikipedia.org/wiki/Orbital_eccentricity), [RAAN](https://en.wikipedia.org/wiki/Right_ascension_of_the_ascending_node), [Argument of Perigee](https://en.wikipedia.org/wiki/Argument_of_periapsis), [Mean Motion](https://en.wikipedia.org/wiki/Mean_motion), [BSTAR Drag Term](https://en.wikipedia.org/wiki/BSTAR)), and calculates UTC [Epoch](https://en.wikipedia.org/wiki/Epoch_(astronomy)) timestamps.
- 🔄 **Deduplication Engine**: Database indexing by [NORAD Catalog Number](https://en.wikipedia.org/wiki/Satellite_Catalog_Number) (`norad_cat_id`) and unique `(satellite_id, epoch_datetime)` constraints avoids duplicate record ingestion upon re-uploading.
- 💬 **Offline AI Natural Language Search ([Text-to-SQL](https://en.wikipedia.org/wiki/Semantic_parsing))**:
  - Runs fully offline using [`llama-cpp-python`](https://github.com/abetlen/llama-cpp-python) and the quantized [`GGUF`](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md) model `Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf`.
  - Translates plain English prompts (e.g., *"Find satellites with inclination > 50 degrees"*) into SQL queries.
  - Built-in SQL safety validation filter blocks non-`SELECT` statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, etc.).
- 🔍 **Keyword Search (default Search tab)**: Leave the box empty to list every satellite, or type a term to `ILIKE` match name, NORAD ID, international designator, classification, and raw TLE lines.
- 🌍 **Geo-Spatial & Country Proximity Search**: Computes real-time satellite orbital positions using [SGP4 orbital propagation](https://en.wikipedia.org/wiki/SGP4). The country dropdown is limited to countries with bounding-box data; a prefix table uses the first word of each catalogue name (`CSS (TIANHE)` → `CSS`, `STARLINK-1007` → `STARLINK`).
- 🛰️ **Live 2D & 3D Globe Tracker**: Multi-satellite real-time tracking with [satellite.js](https://github.com/shashwatak/satellite-js). Maps default to **Esri World Dark Gray** (no API key). Set `CARTO_API_KEY` to keep CARTO dark tiles. Use **Full screen** / **Exit full screen** (or Escape) on the satellite detail and tracker maps. Optional overlays (off by default) pin **Weather & quakes** (including million-city temperature trends), **Markets**, **Currencies**, **Flights**, **News**, **Ships**, **Webcams**, and **Cloud DCs** from free public APIs only — see [Data sources & attribution](#-data-sources--attribution).
- 🗄️ **SQLite or PostgreSQL datastore**: First launch opens `/setup` to pick an engine. Settings live in `instance/datastore.json` (outside the database) and can be switched later from **Admin → Database**, with optional row copy. Compose Postgres uses the released `postgres:18.6-alpine` image.
- 🔐 **Admin Management & Google OAuth2**: Protected dashboard for uploads, datastore switch, a read-only **Tables & SQL editor** (row cap, CSV/Excel export, saved queries with p50/p95/p99/p100 latency), seed flags, and GGUF downloads via [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2). Local `/auth/dev-bypass` is disabled when `FLASK_ENV=production`.

---

## 🖼️ Visual Application Feature Showcase

> 💡 **UI Alignment & Component Layout Note**: The visual mockups below showcase high-fidelity conceptual design previews for the application features. The accompanying component layout wireframes map 1-to-1 to the live Flask template elements (`app/templates/report.html`, `app/templates/tracker.html`, `app/templates/upload.html`, `app/templates/admin.html`), including exact field names, performance metrics badges (`⚡ System Performance`), TLE parameters, and dark-mode styling.

### 1. 💬 Offline AI Natural Language Search (Text-to-SQL)
Translates plain English queries into validated read-only SQL queries using local GGUF model inference with real-time CPU system load reporting and execution metrics breakdown.

![AI Natural Language Search Screenshot](docs/images/ai_search.png)

```
+-----------------------------------------------------------------------------------+
| 🛰️ SatTrack Header Navigation                                                     |
| [ 📥 Upload ]  [ 🔍 Search & Report ]  [ 📊 Stats ]  [ 🔐 Admin ]                 |
+-----------------------------------------------------------------------------------+
| Search Mode Tabs: [ 🔍 Keyword Search ]  [ 🌍 Country Proximity ]  [ 💬 AI Search ] |
+-----------------------------------------------------------------------------------+
| 💬 Natural Language AI Search Composer                                            |
| Prompt Input: "Show Starlink satellites with inclination > 53 degrees"            |
| Prompt Chips: [ Starlink over US ] [ Mean motion > 15 ] [ Inclination > 95 ]     |
| [ 🔍 Ask AI Assistant ]                                                          |
+-----------------------------------------------------------------------------------+
| ⚙️ Processing query... (Local GGUF AI inference active — system load expected)    |
| Elapsed Time: 4.2s                                                                |
+-----------------------------------------------------------------------------------+
| ⚡ System Performance: Total 19.74s (LLM Inference: 19.72s · DB: 0.012s)          |
| 🛠️ Generated SQL Query:                                                           |
| SELECT s.norad_cat_id, s.name, t.inclination_deg, t.mean_motion_rev_day           |
| FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id                    |
| WHERE t.inclination_deg > 53.0 LIMIT 50;                                          |
+-----------------------------------------------------------------------------------+
| NORAD ID | Name        | Inclination | Mean Motion (rev/day) | Actions            |
| 44713    | STARLINK-10 | 53.05°      | 15.06                 | [ Track Orbit 🛰️ ] |
| 44714    | STARLINK-11 | 53.06°      | 15.06                 | [ Track Orbit 🛰️ ] |
+-----------------------------------------------------------------------------------+
```

---

### 2. 🛰️ Live 2D Ground Track & 3D Globe Satellite Tracker
Interactive 2D Leaflet ground track map and 3D globe visualization rendering real-time orbital path projections, ground station footings, and position vectors.

![Live 3D Globe Orbit Tracker Screenshot](docs/images/tracker.png)

```
+-----------------------------------------------------------------------------------+
| 🛰️ Live Satellite Orbital Tracker: STARLINK-11 (NORAD #44714)   [ Full screen ]   |
| Latitude: 34.05° N | Longitude: 118.24° W | Altitude: 550.2 km | Velocity: 7.59 km/s|
| Basemap: Esri World Dark Gray (optional CARTO_API_KEY for CARTO dark tiles)       |
| [ Center ] [ Full screen ] [ Weather & quakes ] [ Markets ] [ Currencies ] [ Flights ] [ News ] [ Ships ] [ Webcams ] [ Cloud DCs ] |
| Credits: Esri · NASA EONET · USGS · Open-Meteo · CNBC · Yahoo Finance · Frankfurter · Big Mac Index · OpenSky · GDACS · UN News · Digitraffic AIS |
+-----------------------------------------------------------------------------------+
|  [ 🌍 2D Leaflet Ground Track Map ]       |  [ 🌐 3D Globe Orbit Projection ]     |
|  . . . . . . . . . . . . . . . . . . . .  |          .---.                        |
|  . . . . . . . (🛰️ STARLINK) . . . . . .  |        /       \                      |
|  . . . . . ./~/~~\~\. . . . . . . . . . . |       |    🌍   |  (🛰️ Orbit Vector)  |
|  . . . . . /~/    \~\ . . . . . . . . . . |        \       /                      |
|  . . . . . . . . . . . . . . . . . . . .  |          '---'                        |
+-----------------------------------------------------------------------------------+
```

---

### 3. 📥 3-Line TLE Ingestion & Deduplication Upload Interface
Parses 3-line and 2-line TLE dataset files, verifies modulo-10 checksums, extracts Keplerian elements, and prevents duplicate epoch ingestion.

![TLE Data Upload Interface Screenshot](docs/images/tle_upload.png)

```
+-----------------------------------------------------------------------------------+
| 📥 Upload & Ingest TLE Data File                                                  |
| Select File: [ starlink_constellation_tle.txt ]                                   |
| Session Label: [ April 2025 Constellation Batch ]                                 |
| [ 🚀 Parse & Import TLE Dataset ]                                                |
+-----------------------------------------------------------------------------------+
| 📊 Ingestion Audit Summary Report:                                                |
| Total Records Processed : 1,540                                                   |
| New Satellites Created  : 85                                                      |
| Satellites Updated      : 1,455                                                    |
| Duplicate Epochs Skipped: 0                                                       |
+-----------------------------------------------------------------------------------+
```

---

### 4. 🔐 Protected Admin Dashboard & OAuth Access Control
Administrative interface for managing upload sessions, triggering local GGUF model downloads, clearing seed flags, and monitoring system resource allocations.

![Admin Control Dashboard Screenshot](docs/images/admin_panel.png)

```
+-----------------------------------------------------------------------------------+
| 🔐 Admin Management Center                              Logged in via Google OAuth|
+-----------------------------------------------------------------------------------+
| 🤖 Offline AI Model Management: qwen2.5-coder-1.5b-instruct-q4_k_m.gguf           |
| Status: [ Model Ready / Active ]                                                  |
| Actions: [ 🔄 Download GGUF Model ]  [ 🗑️ Wipe Database ]  [ ⚡ Clear Seed Flag ] |
| Datastore: sqlite | postgres          [ Tables & SQL editor → ]                   |
+-----------------------------------------------------------------------------------+
| Upload History Audit Log:                                                         |
| ID | Filename         | Upload UTC           | Records | Source      | Actions   |
| 1  | kaggle_tle.txt   | 2026-09-02 10:00 UTC | 1,540   | user_upload | [Delete]  |
+-----------------------------------------------------------------------------------+
```

---

## 📚 Domain Terminology Reference Guide

For detailed explanations of space domain, orbital mechanics, and artificial intelligence terminology used in this application, please refer to the following authoritative resources:

| Term / Acronym | Definition & Domain | Reference Link |
| :--- | :--- | :--- |
| **TLE** | Two-Line Element Set format for satellite orbital state vectors | [CelesTrak TLE Guide](https://celestrak.org/columns/v04n03/) / [Wikipedia](https://en.wikipedia.org/wiki/Two-line_element_set) |
| **NORAD Catalog ID** | 5-digit sequential number assigned by USSPACECOM | [Wikipedia: Satellite Catalog Number](https://en.wikipedia.org/wiki/Satellite_Catalog_Number) |
| **SGP4** | Simplified General Perturbations model 4 for satellite orbit propagation | [Space-Track.org Documentation](https://www.space-track.org/) / [Wikipedia](https://en.wikipedia.org/wiki/SGP4) |
| **Inclination** | Vertical tilt of the satellite's orbit relative to Earth's equator (degrees) | [Wikipedia: Orbital inclination](https://en.wikipedia.org/wiki/Orbital_inclination) |
| **Eccentricity** | Shape of the orbit (0 = circular, 0 < e < 1 = elliptical) | [Wikipedia: Orbital eccentricity](https://en.wikipedia.org/wiki/Orbital_eccentricity) |
| **RAAN** | Right Ascension of the Ascending Node (longitude of orbital node) | [Wikipedia: RAAN](https://en.wikipedia.org/wiki/Right_ascension_of_the_ascending_node) |
| **Argument of Perigee** | Angle between ascending node and satellite's closest point to Earth | [Wikipedia: Argument of periapsis](https://en.wikipedia.org/wiki/Argument_of_periapsis) |
| **Mean Motion** | Number of complete revolutions a satellite completes per day (rev/day) | [Wikipedia: Mean motion](https://en.wikipedia.org/wiki/Mean_motion) |
| **BSTAR Drag** | Model parameter representing atmospheric drag force on the satellite | [Wikipedia: BSTAR](https://en.wikipedia.org/wiki/BSTAR) |
| **Epoch** | Specific UTC time instant at which the orbital parameters were measured | [Wikipedia: Epoch (astronomy)](https://en.wikipedia.org/wiki/Epoch_(astronomy)) |
| **GGUF** | Binary file format for compact LLM quantization and execution | [GGML / GGUF Specification](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md) |
| **Text-to-SQL** | Natural language processing technique mapping text to database SQL queries | [Wikipedia: Semantic parsing](https://en.wikipedia.org/wiki/Semantic_parsing) |

---

## 📖 Documentation & Architecture

Detailed project architecture and design documentation are available in the repository and published on **[GitHub Pages](https://sethusrinivasan.github.io/satellite-tracker/)**:

- 🏗️ **[Architecture Overview](docs/architecture.md)** — Blueprints, database ER diagram, security filters, and offline LLM engine.
- 🛡️ **[Threat Model & Risk Analysis](docs/threat_model.md)** — STRIDE risk categorization matrix, SQL injection prevention, and security controls.
- 🔒 **[Security Policy](SECURITY.md)** — Vulnerability reporting and production auth/SQL rules.
- 🎨 **[Design System & UI/UX](docs/design.md)** — Dark mode palette, visual tokens, and responsive layout guidelines.
- 📌 **[Known Issues & TODO Roadmap](docs/known_issues.md)** — Tracked technical limitations, workarounds, and enhancement items on [GitHub Issues](https://github.com/sethusrinivasan/satellite-tracker/issues).
- 📋 **[Software Bill of Materials (SBOM)](sbom.json)** — Machine-readable CycloneDX 1.5 JSON dependency inventory.
- 📑 **[GitHub Pages Documentation Site](docs/index.md)** — Hosted project documentation.


---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.9+**
- `gcc` / C++ compiler (required for compiling `llama-cpp-python` C++ bindings)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/sethusrinivasan/satellite-tracker.git
cd satellite-tracker

# Preferred: run.sh recreates an incomplete venv (Debian without python3-venv)
bash run.sh

# Or create the venv yourself
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If `data/kaggle_tle_data.txt` is missing, first launch seeds a small **demo** TLE set (`source=demo`) so Search and Upload have rows to show.

### 3. Environment Configuration (Optional for OAuth)

Copy the `.env.example` file to create a local `.env`:

```bash
cp .env.example .env
```

To enable Google OAuth for the Admin panel:
1. Obtain Google OAuth credentials from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
3. Set `ADMIN_ALLOWED_EMAILS` to restrict access to authorized user emails.

Google does not force the account picker on every visit. After a successful sign-in the admin session lasts **14 days** (`ADMIN_SESSION_DAYS`) and refreshes while you use the app. Use **Sign out** to clear it.

Optional: `CARTO_API_KEY` keeps CARTO dark map tiles. Without it, Live Orbit Tracking uses Esri World Dark Gray.

Optional PostHog web analytics: create a project at [PostHog](https://us.posthog.com), copy the **Project API key** (`phc_…`), and set `POSTHOG_PROJECT_API_KEY` in `.env`. Use `POSTHOG_HOST=https://eu.i.posthog.com` for EU cloud. Session replay stays off unless `POSTHOG_SESSION_REPLAY=true`. Pageviews and autocapture then appear under **Web analytics**.

On first launch without `DATABASE_URL` / `DB_ENGINE`, open **[http://localhost:5000/setup](http://localhost:5000/setup)** and choose SQLite or PostgreSQL. You can switch later from **Admin → Database**.

### 4. Running the Application

```bash
# Using the run script
bash run.sh

# Or directly with Python
python3 run.py
```

Open your browser and navigate to **[http://localhost:5000](http://localhost:5000)**.

---

## 🚀 Cloud & 1-Click Deployment Options

> ⚠️ **Important Billing & Cost Disclaimer**: Prior to deploying to commercial cloud providers (AWS, GCP, Azure, DigitalOcean, Render), please carefully review the respective provider's pricing structures, billing policies, and free tier quotas. Running continuous container instances or GGUF AI model workloads may incur cloud compute costs depending on instance sizing and runtime duration.

### 🆓 Free-Tier Hosting Options (No Credit Card Required)

#### 1. Hugging Face Spaces (Recommended for AI Models — Free CPU Tier)
Hugging Face Spaces offers a **free 16 GB RAM CPU tier** with zero credit card requirements, ideal for hosting GGUF local model inference:

[![Deploy to Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Create_Docker_Space-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/new-space)

There is no hosted Space for this repo yet. The button opens Hugging Face’s **create Space** page (not a live demo).

1. Create a free Space and select **Docker** as the SDK.
2. Connect GitHub repository `sethusrinivasan/satellite-tracker`.

#### 2. PythonAnywhere (Free Tier Web Host — No Credit Card Required)
PythonAnywhere offers a **free beginner tier** for Python/Flask web applications:

[![PythonAnywhere](https://img.shields.io/badge/PythonAnywhere-Free_Tier_Flask_Hosting-3572A5?style=for-the-badge&logo=python&logoColor=white)](https://www.pythonanywhere.com/)

No PythonAnywhere demo is published. That badge is only a link to their signup / dashboard so you can host your own copy.

---

### ☁️ Major Commercial Cloud Providers (1-Click Deployments)

#### 1. Google Cloud Platform (GCP Cloud Run)
Deploy directly to serverless Google Cloud Run using the container [`Dockerfile`](Dockerfile):

[![Deploy to Cloud Run](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/sethusrinivasan/satellite-tracker.git)

#### 2. DigitalOcean App Platform
Launch a managed app container on DigitalOcean App Platform:

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/sethusrinivasan/satellite-tracker/tree/main)

#### 3. Amazon Web Services (AWS App Runner / ECS)
Deploy containerized workloads to AWS App Runner or Amazon ECS:

[![Deploy to AWS](https://img.shields.io/badge/AWS-App_Runner_/_ECS-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://console.aws.amazon.com/apprunner)

#### 4. Microsoft Azure App Service
Deploy Linux web app containers to Azure App Service:

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template)

#### 5. Render Web Services
Deploy to Render using GitHub repository integration:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sethusrinivasan/satellite-tracker)

---

### 🐳 Self-Hosted Container Deployment (Docker — Free / Open Source)
Build and run on any local machine or self-hosted server with zero external dependencies or costs:

```bash
# Option A: One-step build and run via helper script
./run.sh --docker

# Option B: Standard Docker CLI commands
docker build -t satellite-tracker:latest .
docker run -p 5000:5000 --env-file .env satellite-tracker:latest
```

#### 🔄 Local Docker Compose (build, wizard, and tests)

Use Compose for a local build with a persistent `instance/` volume. The first visit opens a setup wizard to choose **SQLite** or **PostgreSQL**. You can switch engines later from **Admin → Database**.

`run.sh` exports `SATTRACK_UID` / `SATTRACK_GID` so `instance/datastore.json` is not created as `root:root` mode `600` (that causes `Permission denied` when you later run `./run.sh --local`).

```bash
# SQLite (default) — first-launch datastore wizard at http://localhost:5000/setup
docker compose up --build
# or: ./run.sh --compose

# App + PostgreSQL 18.6 — pick PostgreSQL in the wizard (host: postgres)
docker compose --profile postgres up --build
# or: ./run.sh --compose-postgres

# Tests
docker compose --profile test run --rm test
docker compose --profile test-postgres run --rm test-postgres
```

Headless bootstrap (skips the wizard): set `DATABASE_URL` or `DB_ENGINE` in `.env`. Example for Compose Postgres:

```
DATABASE_URL=postgresql+psycopg://sattrack:sattrack@postgres:5432/sattrack
```

#### 🔄 Automated CI/CD Docker Publishing
[![CI](https://github.com/sethusrinivasan/satellite-tracker/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/sethusrinivasan/satellite-tracker/actions/workflows/docker-publish.yml)

GitHub Actions (`.github/workflows/docker-publish.yml`) runs pytest and builds the container on `main` and on pull requests. Images are pushed to GHCR (and Docker Hub, if those secrets are set) only when the checked-in [`VERSION`](VERSION) file is bumped to a new semantic version. There is no published image until that bump happens.

---

## 🤖 Setting Up Offline AI Search

1. Navigate to the **Admin Panel** (`/admin`).
2. Under **Offline AI Model Management**, click **Download Model**.
3. The system will stream the `Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf` file (~900MB) from HuggingFace to `app/models/`.
4. Once downloaded, switch to the **💬 AI Search** tab on the main page to ask natural language questions!

---

## 📁 Repository Structure

```
satellite-tracker/
├── app/
│   ├── models/            # Directory for local GGUF model binaries (git-ignored)
│   ├── routes/
│   │   ├── admin.py       # Admin dashboard, datastore switch, SQL explorer
│   │   ├── auth.py        # Google OAuth2 login & fail-closed local bypass
│   │   ├── report.py      # Keyword, proximity, Text-to-SQL, & tracker routes
│   │   ├── setup.py       # First-launch SQLite / PostgreSQL wizard
│   │   └── upload.py      # GET form + POST ingest & seed auto-import
│   ├── services/
│   │   ├── datastore.py   # Engine URI, schema ensure, snapshot migrate
│   │   ├── demo_tle.py    # Bundled demo TLEs when Kaggle file is absent
│   │   ├── db_service.py  # SQLAlchemy persistence & deduplication logic
│   │   ├── geo_query_service.py # SGP4, country list, name prefixes
│   │   ├── sql_console.py # Read-only admin SQL, saved queries, latency
│   │   ├── overlay_cache.py # Shared overlay cache (per-feed TTL, stale-while-revalidate)
│   │   ├── overlay_http.py # Overlay HTTP + 429/Retry-After host backoff
│   │   ├── world_events.py # NASA EONET weather/climate + USGS quakes
│   │   ├── city_temperature.py # Million-city 7d/30d/90d/1y temps (Open-Meteo)
│   │   ├── market_indices.py # CNBC index levels + Yahoo 7d–10y %
│   │   ├── currency_overlay.py # Local units per USD/EUR/yen/gold/oil/Big Mac
│   │   ├── flight_overlay.py # OpenSky Network airborne positions
│   │   ├── news_overlay.py # Last-24h GDACS + UN / Global Voices / Conversation / DW pins
│   │   ├── shipping_overlay.py # Sea lanes + Digitraffic AIS
│   │   ├── webcam_overlay.py # Official + OSM public webcam pins
│   │   ├── cloud_datacenters.py # AWS / Azure / GCP pins + HTTPS ping p50/p95/p99
│   │   └── tle_parser.py  # TLE line format parsing & checksum validation
│   ├── static/            # CSS & JS (basemap.js, datastore.js, tracker.js)
│   ├── templates/         # Jinja2 HTML (setup, admin_database, report, …)
│   └── models.py          # Satellite, TLEElement, Upload, SavedQuery
├── docker-compose.yml     # App + postgres:18.6-alpine + test profiles
├── docker/postgres-init/  # Extra test database for Compose pytest
├── data/                  # Local directory for user datasets (git-ignored)
├── docs/
│   ├── index.md           # GitHub Pages landing page
│   ├── architecture.md    # System architecture & database schema
│   └── design.md          # UI/UX design tokens & visual components
├── instance/              # SQLite database & file upload storage (git-ignored)
├── config.py              # Application settings
├── requirements.txt       # Dependencies
├── run.py                 # Application launcher
└── run.sh                 # Convenience execution script
```

---

## 🌐 Data sources & attribution

Tracker overlays use **free, no-key (or optional free-key) public resources only**. The map credit strip and each popup name the source. Clicking a **News** title opens the publisher article in a new tab (`target="_blank"` `rel="noopener noreferrer"`).

| Layer | What you see | Free source | Attribution / terms |
| :--- | :--- | :--- | :--- |
| **Basemap** (default) | Dark gray canvas + labels | [Esri World Dark Gray](https://www.arcgis.com/home/item.html?id=5e9b0127f7bb40c2a087e935c7231d76) | Tiles © Esri — Esri, HERE, Garmin, FAO, NOAA, USGS. Reasonable non-commercial use; no Esri API key. |
| **Basemap** (optional) | CARTO `dark_all` | [CARTO basemaps](https://carto.com/basemaps/) + [OpenStreetMap](https://www.openstreetmap.org/copyright) | © OpenStreetMap contributors © [CARTO](https://carto.com/attributions). Requires a free `CARTO_API_KEY`. |
| **Weather & quakes** | Weather/climate events plus M4.5+ earthquakes, plus **temperature trend pins** for cities over 1 million people (latest daily mean and 7d / 30d / 90d / 1y °C change). Quake bubbles scale **size and color by magnitude**. Temp pins color by the 7-day change (blue cooler, red warmer). | [NASA EONET](https://eonet.gsfc.nasa.gov/) · [USGS](https://earthquake.usgs.gov/) · [Open-Meteo](https://open-meteo.com/) ERA5 archive | NASA public information; USGS is U.S. Government public-domain data. City temperatures are Open-Meteo daily 2 m means (ERA5 / Copernicus, CC BY 4.0). ERA5 can lag a few days; the popup shows the last available date. |
| **Markets** | Major world indexes (60+). Level and **1d %** from CNBC. **7d / 30d / 1q / 6m / 1y / 2y / 5y / 10y %** are calculated locally from Yahoo Finance daily closes (ETF proxy where an index series is missing). Pin color is the 1-day change. | [CNBC](https://www.cnbc.com) public quotes · [Yahoo Finance](https://finance.yahoo.com) chart daily history | Index levels from CNBC public quotes. Longer-horizon % use Yahoo daily closes, cached about an hour, and are not a paid market-data feed. Rank/cap figures are approximate, not a live cap feed. |
| **Currencies** | Local units needed to buy **1 USD, 1 EUR, 1 yen, 1 oz gold, 1 barrel of oil (WTI), and 1 Big Mac**. FX/gold also show 1d / 7d / 30d / 90d / 6m / 1y / 5y %. Pin color is the 1-day change vs USD (more local per $1 = weaker = red). | [Frankfurter](https://frankfurter.dev) daily FX + XAU · [CNBC](https://www.cnbc.com/quotes/@CL.1) WTI · [The Economist Big Mac Index](https://github.com/TheEconomist/big-mac-data) | End-of-day FX and gold from Frankfurter (official / central-bank sources). Oil is the public CNBC WTI crude quote converted at the local-per-USD rate. Big Mac local prices are The Economist’s published index, not a live restaurant feed. |
| **Flights** | Airborne aircraft in the current map view. Tooltip/popup state origin, destination, and estimated on-time vs delayed. | [The OpenSky Network](https://opensky-network.org) REST `/api/states/all` · [adsbdb](https://www.adsbdb.com) callsign routes | Aircraft positions from The OpenSky Network (Schäfer et al., IPSN 2014). Routes are usual callsign city pairs from adsbdb, not a guaranteed flight plan. On-time is estimated from first-seen time vs typical duration, not an airline schedule. |
| **News** | Alerts and headlines from the last 24 hours, pinned at published or gazetteer coordinates. Hover shows a short title; click opens the article. | [GDACS](https://www.gdacs.org) GeoJSON · [UN News](https://news.un.org) RSS · [Global Voices](https://globalvoices.org) (CC BY 3.0) · [The Conversation](https://theconversation.com) (CC BY-ND) · [Deutsche Welle](https://www.dw.com) RSS | Free-reuse or attributed RSS/GeoJSON only. Wikipedia featured was dropped (too old). Items without a usable place stay off the map. |
| **Ships** | Current AIS positions at that moment | [Fintraffic Digitraffic](https://www.digitraffic.fi/en/marine-traffic/) AIS | Live positions are **Finland/Baltic only**, CC BY 4.0. Hover a vessel for its latest location and timestamp. |
| **Webcams** | Official public camera pages worldwide; extra OSM pins around world hubs and when zoomed in. Click the title to open the publisher page. | USGS · NPS · NOAA · [INGV](https://ingv.it/en/real-time-data-volcanoes-maps) · [GeoNet](https://www.geonet.org.nz/volcano/cameras) · vegvesen · foto-webcam.eu · Traffic Scotland · MSS Singapore · USAP McMurdo · [OpenStreetMap](https://www.openstreetmap.org/copyright) via [Overpass](https://overpass-api.de/) | We link out; we do not host the video. OSM webcam URLs are © OpenStreetMap contributors, ODbL. |
| **Cloud DCs** | AWS (orange), Azure (blue), and GCP (green) region pins. Tooltip shows HTTPS ping **p50 / p95 / p99** measured from this SatTrack server. | [AWS DynamoDB /ping](https://docs.aws.amazon.com/general/latest/gr/ddb.html) · [Azure Speed Test](https://www.azurespeed.com/) public blobs · [GCPing](https://www.gcping.com/) Cloud Run | City-level public geography, not a building address. Latency is HTTPS round-trip (not ICMP) from the app host. Pins render immediately; pings fill in. Cached ~90s. |
| **TLE seed** (optional) | Catalogue ingest | [CelesTrak](https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle) | Download and upload locally. A former Kaggle Starlink dump is gone from that URL; if `data/kaggle_tle_data.txt` is missing, the app seeds bundled demo TLEs (`source=demo`). |
| **Offline AI model** | Text-to-SQL | [Qwen2.5-Coder](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct) via Hugging Face | Model card / license on Hugging Face. Inference stays in-process (`llama-cpp-python`). |
| **Web analytics** (optional) | Pageviews | [PostHog](https://posthog.com) | Loaded only if `POSTHOG_PROJECT_API_KEY` is set. |

No paid market-data, ADS-B, or news APIs are called. Overlay routes do not forward user search text to third parties.

---

## 📊 Sample Datasets & Reference Data

Sample TLE datasets can be retrieved directly from public orbital data sources or Kaggle:

1. **CelesTrak Active Satellites TLE Data**:  
   [CelesTrak Active Satellites](https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle) — Real-time active satellite element sets. Download and upload via `/upload`.
2. **Local seed file**: Save a TLE text file as `data/kaggle_tle_data.txt` for auto-seeding. If that file is absent, the app inserts bundled demo TLEs marked `source=demo`. (The old Kaggle Starlink dump that used to be linked here returns 404.)

---

## 🤖 AI Assistance Acknowledgment

This repository and codebase were developed with pair-programming assistance from **Antigravity**, an AI agentic coding assistant developed by Google DeepMind. AI tools were used to generate initial code scaffolding, assist with architectural documentation, draft threat models, and format dependency inventories. All code, security controls, and design decisions have been thoroughly reviewed and validated by human maintainers.

---

## 🤝 Contributing & License

This demonstration project is open-source under the [MIT License](LICENSE). Contributions, bug reports, feature suggestions, and enhancements are welcome! Feel free to fork, adapt, and build upon this project.
