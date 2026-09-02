# 🛰️ Satellite TLE Tracker & AI Orbital Discovery

Welcome to the official documentation for **Satellite TLE Tracker & AI Orbital Discovery**.

> **Elevator Pitch**: An open-source web application built with Flask, SQLite, and SGP4 orbit propagation that organizes satellite Two-Line Element (TLE) datasets and enables offline natural language querying without external cloud dependencies.

---

## 🧭 Documentation Portal

| Document | Description | Target Audience |
| :--- | :--- | :--- |
| 🏗️ **[System Architecture](architecture.md)** | Flask blueprints, ORM schema, SGP4 propagation pipeline, and offline LLM execution | Developers & Architects |
| 🛡️ **[Threat Model & Risk Analysis](threat_model.md)** | STRIDE security matrix, read-only SQL validation rules, and threat mitigations | Security & Compliance |
| 🎨 **[Design System & UX](design.md)** | Dark-mode color palette, responsive layout rules, and component patterns | UI/UX Designers & Frontend |
| 📌 **[Known Issues & Roadmap](known_issues.md)** | Tracked technical limitations, workarounds, and enhancement items | All Users & Contributors |
| 📋 **[Software Bill of Materials](../sbom.json)** | CycloneDX 1.5 JSON dependency inventory covering Python and JS packages | Security & Supply Chain |
| 💻 **[GitHub Repository](https://github.com/sethusrinivasan/satellite-tracker)** | Source code, open-source issue tracker, and contribution guide | Open Source Contributors |

---

## 💡 Key Functionality

- **Offline Natural Language Search (Text-to-SQL)**: Converts natural language questions (e.g. *"Show Starlink satellites with mean motion > 15"*) into read-only SQL queries via `llama-cpp-python` and Qwen2.5-Coder running completely offline.
- **Orbital Propagation Engine**: Evaluates real-time satellite locations over regions like the **United States** using SGP4 orbital mechanics algorithms.
- **Live Orbit & Telemetry Tracking**: Renders 2D ground track paths and 3D globe visualizations with latitude, longitude, altitude, and velocity calculations.
- **Dataset Ingestion & Deduplication**: Parses 3-line TLE files, enforces unique catalog indexing (`norad_cat_id`), and skips duplicate epoch records.

---

## 🚀 One-Click Cloud Deployment Options

Deploy a live instance of the platform to free hosting providers:

- **Deploy to Render**: [![Deploy to Render](https://render.com/images/deploy-to-render.svg)](https://render.com/deploy?repo=https://github.com/sethusrinivasan/satellite-tracker)
- **Deploy to Railway**: [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)
- **Hugging Face Spaces**: Docker SDK Space (16 GB Free RAM) via [Hugging Face Spaces](https://huggingface.co/new-space)

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

