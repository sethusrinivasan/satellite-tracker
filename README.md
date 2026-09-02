# 🛰️ Satellite TLE Tracker & AI Orbital Discovery

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-SQLAlchemy-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlalchemy.org/)
[![Offline AI](https://img.shields.io/badge/Offline_AI-llama--cpp--python-FF6F00?style=flat-square&logo=huggingface&logoColor=white)](https://github.com/abetlen/llama-cpp-python)
[![SBOM](https://img.shields.io/badge/SBOM-CycloneDX_v1.5-blue?style=flat-square&logo=json)](sbom.json)
[![GitHub Pages](https://img.shields.io/badge/Docs-GitHub_Pages-22C55E?style=flat-square&logo=github&logoColor=white)](https://sethusrinivasan.github.io/satellite-tracker/)

A demonstration and experimental Flask web application for uploading, parsing, exploring, and tracking satellite [Two-Line Element (TLE)](https://en.wikipedia.org/wiki/Two-line_element_set) data. Features real-time [SGP4 (Simplified General Perturbations 4)](https://en.wikipedia.org/wiki/Simplified_General_Perturbations_models) orbit propagation, country proximity filtering, interactive 2D/3D map tracking, and an **in-process offline Text-to-SQL AI natural language search** powered by [Qwen2.5-Coder](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct).

> ℹ️ **Project Status & Disclaimer**: This is an open demonstration and proof-of-concept project intended for educational, research, and experimental exploration. No production-grade assurances or SLAs are guaranteed. Please feel free to review, copy, fork, adapt, and enhance the code for your own projects!

---

## 🌟 Key Features

- 🛰️ **3-Line TLE Ingestion & Parsing**: Parses standard [TLE format](https://celestrak.org/columns/v04n03/) records, extracts key [Keplerian orbital elements](https://en.wikipedia.org/wiki/Orbital_elements) ([Inclination](https://en.wikipedia.org/wiki/Orbital_inclination), [Eccentricity](https://en.wikipedia.org/wiki/Orbital_eccentricity), [RAAN](https://en.wikipedia.org/wiki/Right_ascension_of_the_ascending_node), [Argument of Perigee](https://en.wikipedia.org/wiki/Argument_of_periapsis), [Mean Motion](https://en.wikipedia.org/wiki/Mean_motion), [BSTAR Drag Term](https://en.wikipedia.org/wiki/BSTAR)), and calculates UTC [Epoch](https://en.wikipedia.org/wiki/Epoch_(astronomy)) timestamps.
- 🔄 **Deduplication Engine**: Database indexing by [NORAD Catalog Number](https://en.wikipedia.org/wiki/Satellite_Catalog_Number) (`norad_cat_id`) and unique `(satellite_id, epoch_datetime)` constraints avoids duplicate record ingestion upon re-uploading.
- 💬 **Offline AI Natural Language Search ([Text-to-SQL](https://en.wikipedia.org/wiki/Text-to-SQL))**:
  - Runs 100% offline using [`llama-cpp-python`](https://github.com/abetlen/llama-cpp-python) and the quantized [`GGUF`](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md) model `Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf`.
  - Translates plain English prompts (e.g., *"Find satellites with inclination > 50 degrees"*) into SQL queries.
  - Built-in SQL safety validation filter blocks non-`SELECT` statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, etc.).
- 🌍 **Geo-Spatial & Country Proximity Search**: Computes real-time satellite orbital positions using [SGP4 orbital propagation](https://en.wikipedia.org/wiki/Simplified_General_Perturbations_models) to discover satellites currently passing over specific countries or geographical bounding boxes.
- 🛰️ **Live 2D & 3D Globe Tracker**: Multi-satellite real-time tracking interface showing ground track coordinates, altitude, velocity, and orbital path projections rendered via [satellite.js](https://github.com/shashwatak/satellite-js).
- 🔐 **Admin Management & Google OAuth2**: Protected dashboard for managing uploads, database resets, clearing seed flags, and monitoring local GGUF model downloads secured via [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2).

---

## 📚 Domain Terminology Reference Guide

For detailed explanations of space domain, orbital mechanics, and artificial intelligence terminology used in this application, please refer to the following authoritative resources:

| Term / Acronym | Definition & Domain | Reference Link |
| :--- | :--- | :--- |
| **TLE** | Two-Line Element Set format for satellite orbital state vectors | [CelesTrak TLE Guide](https://celestrak.org/columns/v04n03/) / [Wikipedia](https://en.wikipedia.org/wiki/Two-line_element_set) |
| **NORAD Catalog ID** | 5-digit sequential number assigned by USSPACECOM | [Wikipedia: Satellite Catalog Number](https://en.wikipedia.org/wiki/Satellite_Catalog_Number) |
| **SGP4** | Simplified General Perturbations model 4 for satellite orbit propagation | [Space-Track.org Documentation](https://www.space-track.org/) / [Wikipedia](https://en.wikipedia.org/wiki/Simplified_General_Perturbations_models) |
| **Inclination** | Vertical tilt of the satellite's orbit relative to Earth's equator (degrees) | [Wikipedia: Orbital inclination](https://en.wikipedia.org/wiki/Orbital_inclination) |
| **Eccentricity** | Shape of the orbit (0 = circular, 0 < e < 1 = elliptical) | [Wikipedia: Orbital eccentricity](https://en.wikipedia.org/wiki/Orbital_eccentricity) |
| **RAAN** | Right Ascension of the Ascending Node (longitude of orbital node) | [Wikipedia: RAAN](https://en.wikipedia.org/wiki/Right_ascension_of_the_ascending_node) |
| **Argument of Perigee** | Angle between ascending node and satellite's closest point to Earth | [Wikipedia: Argument of periapsis](https://en.wikipedia.org/wiki/Argument_of_periapsis) |
| **Mean Motion** | Number of complete revolutions a satellite completes per day (rev/day) | [Wikipedia: Mean motion](https://en.wikipedia.org/wiki/Mean_motion) |
| **BSTAR Drag** | Model parameter representing atmospheric drag force on the satellite | [Wikipedia: BSTAR](https://en.wikipedia.org/wiki/BSTAR) |
| **Epoch** | Specific UTC time instant at which the orbital parameters were measured | [Wikipedia: Epoch (astronomy)](https://en.wikipedia.org/wiki/Epoch_(astronomy)) |
| **GGUF** | Binary file format for compact LLM quantization and execution | [GGML / GGUF Specification](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md) |
| **Text-to-SQL** | Natural language processing technique mapping text to database SQL queries | [Wikipedia: Text-to-SQL](https://en.wikipedia.org/wiki/Text-to-SQL) |

---

## 📖 Documentation & Architecture

Detailed project architecture and design documentation are available in the repository and published on **[GitHub Pages](https://sethusrinivasan.github.io/satellite-tracker/)**:

- 🏗️ **[Architecture Overview](docs/architecture.md)** — Blueprints, database ER diagram, security filters, and offline LLM engine.
- 🛡️ **[Threat Model & Risk Analysis](docs/threat_model.md)** — STRIDE risk categorization matrix, SQL injection prevention, and security controls.
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

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration (Optional for OAuth)

Copy the `.env.example` file to create a local `.env`:

```bash
cp .env.example .env
```

To enable Google OAuth for the Admin panel:
1. Obtain Google OAuth credentials from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
3. Set `ADMIN_ALLOWED_EMAILS` to restrict access to authorized user emails.

### 4. Running the Application

```bash
# Using the run script
bash run.sh

# Or directly with Python
python3 run.py
```

Open your browser and navigate to **[http://localhost:5000](http://localhost:5000)**.

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
│   │   ├── admin.py       # Admin dashboard & AI model download endpoints
│   │   ├── auth.py        # Google OAuth2 login & session management
│   │   ├── report.py      # Search, natural language Text-to-SQL, & API routes
│   │   └── upload.py      # File ingestion & seed auto-import
│   ├── services/
│   │   ├── db_service.py  # SQLAlchemy persistence & deduplication logic
│   │   ├── geo_query_service.py # SGP4 propagation & bounding box filtering
│   │   └── tle_parser.py  # TLE line format parsing & checksum validation
│   ├── static/            # CSS & JS assets
│   ├── templates/         # Jinja2 HTML templates
│   └── models.py          # SQLAlchemy ORM models (Satellite, TLEElement, Upload)
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

## 📊 Sample Datasets & Reference Data

Sample TLE datasets can be retrieved directly from public orbital data sources or Kaggle:

1. **Starlink Satellite TLE Dataset** (Kaggle):  
   [Starlink Satellite TLE CSV Dataset](https://www.kaggle.com/datasets/vijayj0shi/starlink-satellite-tlecsv-dataset-april-2025?select=starlink_tle.txt) by Vijay Joshi. Save the raw text file to `data/kaggle_tle_data.txt` for local auto-seeding.
2. **CelesTrak Active Satellites TLE Data**:  
   [CelesTrak Active Satellites](https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle) — Real-time active satellite element sets. Download and upload directly via the web UI at `/upload`.

---

## 🤖 AI Assistance Acknowledgment

This repository and codebase were developed with pair-programming assistance from **Antigravity**, an AI agentic coding assistant developed by Google DeepMind. AI tools were used to generate initial code scaffolding, assist with architectural documentation, draft threat models, and format dependency inventories. All code, security controls, and design decisions have been thoroughly reviewed and validated by human maintainers.

---

## 🤝 Contributing & License

This demonstration project is open-source under the [MIT License](LICENSE). Contributions, bug reports, feature suggestions, and enhancements are welcome! Feel free to fork, adapt, and build upon this project.

