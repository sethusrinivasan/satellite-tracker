# 🛰️ Satellite TLE Tracker & AI Orbital Discovery

[![GitHub Repository](https://img.shields.io/badge/GitHub-sethusrinivasan%2Fsatellite--tracker-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/sethusrinivasan/satellite-tracker)

Welcome to the official documentation for **Satellite TLE Tracker & AI Orbital Discovery**.

📁 **Official GitHub Repository**: [https://github.com/sethusrinivasan/satellite-tracker](https://github.com/sethusrinivasan/satellite-tracker)

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

## 🚀 Cloud & 1-Click Deployment Options

> ⚠️ **Cost & Billing Notice**: Please review the respective cloud provider's pricing schedule and free tier terms before deploying to commercial platforms (GCP, AWS, Azure, DigitalOcean, Render).

### 🆓 Free-Tier Hosting (No Credit Card Required)
- **Hugging Face Spaces (Free 16 GB RAM)**: [![Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces_Docker_(Free_Tier)-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co/new-space)
- **PythonAnywhere (Free Flask Host)**: [![PythonAnywhere](https://img.shields.io/badge/PythonAnywhere-Free_Tier_Flask-3572A5?style=flat-square&logo=python&logoColor=white)](https://www.pythonanywhere.com/)

### ☁️ Major Cloud Providers (1-Click Deployments)
- **Google Cloud Platform (GCP Cloud Run)**: [![Deploy to Cloud Run](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/sethusrinivasan/satellite-tracker.git)
- **DigitalOcean App Platform**: [![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/sethusrinivasan/satellite-tracker/tree/main)
- **AWS App Runner / ECS**: [![Deploy to AWS](https://img.shields.io/badge/AWS-App_Runner_/_ECS-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)](https://console.aws.amazon.com/apprunner)
- **Azure App Service**: [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template)

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

