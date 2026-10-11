# 🛰️ Satellite TLE Tracker & AI Orbital Discovery

[![Live Demo on Vercel](https://img.shields.io/badge/Live_Demo-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://sethusrinivasan-satellite-tracker.vercel.app)
[![GitHub Pages Website](https://img.shields.io/badge/Website-GitHub_Pages-22C55E?style=flat-square&logo=github&logoColor=white)](https://sethusrinivasan.github.io/satellite-tracker/)
[![GitHub Repository](https://img.shields.io/badge/GitHub-sethusrinivasan%2Fsatellite--tracker-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/sethusrinivasan/satellite-tracker)
[![CI](https://github.com/sethusrinivasan/satellite-tracker/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/sethusrinivasan/satellite-tracker/actions/workflows/docker-publish.yml)
[![Version](https://img.shields.io/badge/version-0.1.1-blue.svg?style=flat-square)](https://github.com/sethusrinivasan/satellite-tracker/blob/main/VERSION)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://github.com/sethusrinivasan/satellite-tracker/blob/main/LICENSE)

Welcome to the official documentation for **Satellite TLE Tracker & AI Orbital Discovery**.

🚀 **Live Web Application (Vercel)**: [https://sethusrinivasan-satellite-tracker.vercel.app](https://sethusrinivasan-satellite-tracker.vercel.app)  
🌐 **Official Documentation (GitHub Pages)**: [https://sethusrinivasan.github.io/satellite-tracker/](https://sethusrinivasan.github.io/satellite-tracker/)  
📁 **GitHub Repository**: [https://github.com/sethusrinivasan/satellite-tracker](https://github.com/sethusrinivasan/satellite-tracker)

> **Elevator Pitch**: An open-source web application built with Flask, SQLite or PostgreSQL, and SGP4 orbit propagation that organizes satellite Two-Line Element (TLE) datasets and enables offline natural language querying without external LLM APIs. Optional tracker overlays use only free public feeds (NASA EONET, USGS, Open-Meteo, CNBC, Yahoo Finance, Frankfurter, The Economist Big Mac Index, OpenSky, GDACS, UN News, Global Voices, The Conversation, Deutsche Welle, Fintraffic Digitraffic AIS, official webcams, OpenStreetMap, AWS / Azure / GCP ping endpoints) and are attributed in the README.

---

## 🧭 Documentation Portal

| Document | Description | Target Audience |
| :--- | :--- | :--- |
| 🏗️ **[System Architecture](architecture.md)** | Flask blueprints, ORM schema, SGP4 propagation pipeline, and offline LLM execution | Developers & Architects |
| 🛡️ **[Threat Model & Risk Analysis](threat_model.md)** | STRIDE security matrix, read-only SQL validation rules, and threat mitigations | Security & Compliance |
| 🔒 **[Security Policy](https://github.com/sethusrinivasan/satellite-tracker/blob/main/SECURITY.md)** | Vulnerability reporting, production auth bypass rules, admin SQL constraints | Operators & Researchers |
| 🎨 **[Design System & UX](design.md)** | Dark-mode color palette, responsive layout rules, and component patterns | UI/UX Designers & Frontend |
| 📌 **[Known Issues & Roadmap](known_issues.md)** | Tracked technical limitations, workarounds, and enhancement items | All Users & Contributors |
| 📋 **[Software Bill of Materials](https://github.com/sethusrinivasan/satellite-tracker/blob/main/sbom.json)** | CycloneDX 1.5 JSON dependency inventory covering Python and JS packages | Security & Supply Chain |
| 📜 **[MIT License](https://github.com/sethusrinivasan/satellite-tracker/blob/main/LICENSE)** | License text (GitHub Pages only serves `/docs`, so this opens the repo file) | All Users & Contributors |
| 💻 **[GitHub Repository](https://github.com/sethusrinivasan/satellite-tracker)** | Source code, open-source issue tracker, and contribution guide | Open Source Contributors |

---

## 💡 Key Functionality

- **Keyword Search (default)**: Empty query lists all satellites; a typed term `ILIKE`s name, NORAD ID, designator, classification, and raw TLE text.
- **Offline Natural Language Search (Text-to-SQL)**: Converts natural language questions (e.g. *"Show Starlink satellites with mean motion > 15"*) into read-only SQL queries via `llama-cpp-python` and Qwen2.5-Coder running completely offline.
- **Orbital Propagation Engine**: Evaluates real-time satellite locations over countries that have geo reference data. Prefix table uses the first word of each catalogue name (`STARLINK-1007` → `STARLINK`).
- **Live Orbit & Telemetry Tracking**: Renders 2D ground tracks and 3D globe views (Esri World Dark Gray by default; optional `CARTO_API_KEY`). Full screen / Escape on satellite detail and tracker maps. Optional **Weather & quakes**, **Markets**, **Currencies**, **Flights**, **News**, **Ships**, **Webcams**, and **Cloud DCs** overlays (free sources; see README attribution). Earthquake bubbles scale by magnitude. Weather & quakes also pins cities over 1 million with 7d / 30d / 90d / 1y temperature change. Currency popups show local units to buy 1 USD / EUR / yen / oz gold / barrel of oil / Big Mac, plus 1d–5y FX/gold %. Ships show current AIS positions in Finnish waters. News and webcam popups use a short title that opens the publisher page in a new tab. Cloud DC tooltips show HTTPS ping p50 / p95 / p99 from this server.
- **Selectable datastore**: First-launch `/setup` picks SQLite or PostgreSQL 18.6; switch later from Admin. **Admin → Database** includes a read-only SQL editor, CSV/Excel export, and saved queries with p50/p95/p99/p100 latency.
- **Pluggable Multi-Tier Caching Architecture**: High-performance in-memory and atomic disk SWR caching built on 6 design patterns (Strategy, Composite, Resilient Fallback, Factory, Cache-Aside/SWR, Façade). Supports external Valkey/Redis via `VALKEY_URL`, embedded `valkeylite` on POSIX systems, and an automatic zero-dependency fallback (Memory + File with `msvcrt` locking) on Windows desktop runtimes and Vercel serverless.


---

## 🚀 Deployment Options

### 1. ⚡ Production Serverless Deployment (Vercel)
- **Live Production App**: [![Live Demo on Vercel](https://img.shields.io/badge/Live_Demo-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://sethusrinivasan-satellite-tracker.vercel.app) — [https://sethusrinivasan-satellite-tracker.vercel.app](https://sethusrinivasan-satellite-tracker.vercel.app) (actively deployed and running).
- **1-Click Deploy**: [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fsethusrinivasan%2Fsatellite-tracker)
- Preconfigured for Vercel Serverless Functions via [`vercel.json`](https://github.com/sethusrinivasan/satellite-tracker/blob/main/vercel.json) using Python WSGI entrypoint `api/index.py`.

### 2. 🐳 Self-Hosted Container Deployment (Docker & Compose)
- **Local Container**: Run `./run.sh --docker` or `docker build -t satellite-tracker . && docker run -p 5000:5000 --env-file .env satellite-tracker`.
- **Docker Compose**: `docker compose up --build` opens `/setup` on first run to pick SQLite or PostgreSQL 18.6. Launch dedicated PostgreSQL with `docker compose --profile postgres up --build`.
- `run.sh` exports `SATTRACK_UID` / `SATTRACK_GID` so `instance/datastore.json` is writable by the host user.

### 3. 🖥️ Native Standalone Desktop Application (Tauri v2)
- **Cross-Platform Installers**: Download standalone `.msi`/`.exe` for Windows, `.dmg` for macOS, and `.AppImage`/`.deb` for Linux without needing Python or Docker installed.
- **Dedicated OS AppData Storage**: Automatically stores user databases and offline AI models in platform-standard application data directories.
- **Waitress WSGI Sidecar**: Fast in-process communication over dynamic localhost loopback with zero external network exposure.


---

## 📱 User Experience & Responsive Design Standard

The web interface is engineered around responsive design principles to ensure consistent usability across platforms:

- **Desktop Displays**: Multi-column dashboard with tabbed search modes, live side-by-side SQL query visualizers, and interactive tracking controls.
- **Tablet & Touch Devices**: Touch-friendly tap targets ($\ge 44\text{px}$), flexbox container wrapping, and gesture-driven map controls.
- **Mobile Browsers**: Collapsible navigation bar, single-column stacked search forms, and scrollable data tables with fixed header headers.
- **Visual Ergonomics**: High-contrast dark theme (`#0b0f19` background, `#f3f4f6` text) designed to minimize eye fatigue during extended data analysis.

---

## 🤖 AI Assistance Acknowledgment

This repository and codebase were developed with pair-programming assistance from **Antigravity**, an AI agentic coding assistant developed by Google DeepMind. AI models were utilized during pair programming to generate code scaffolding, assist in architectural design, author documentation, and format dependency inventories. All code, security controls, and design decisions have been reviewed and validated by human maintainers.

---

## ℹ️ Usage & Contribution Note

This project is released under the [MIT License](https://github.com/sethusrinivasan/satellite-tracker/blob/main/LICENSE) as an open demonstration. You are encouraged to review, adapt, fork, and enhance the code for your own research or software projects.

