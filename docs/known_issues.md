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
- **Status**: Implemented via regex blocklist validation in `app/routes/report.py`.
- **Labels / Tags**: `Antigravity_generated`, `security`, `p0`
- **Tracking**: [Issue #1: Validate SQL Safety Filter](https://github.com/sethusrinivasan/satellite-tracker/issues/1)

### 2. 🟠 [P1] Compact LLM Multi-Table JOIN Edge Cases
- **Summary**: The 1.5B quantized GGUF model (`Qwen2.5-Coder-1.5B-Instruct-Q4_K_M`) accurately translates standard queries into SQL, but may occasionally omit `JOIN tle_elements` on complex prompts referencing orbital parameters.
- **Workaround**: System prompt few-shot examples guide the model toward proper `JOIN` syntax.
- **Labels / Tags**: `Antigravity_generated`, `ai`, `p1`
- **Tracking**: [Issue #2: Improve LLM SQL JOIN reasoning for complex multi-table queries](https://github.com/sethusrinivasan/satellite-tracker/issues/2)

### 3. 🟠 [P1] Local LLM Inference Latency & UI System Load Feedback
- **Summary**: Local CPU GGUF inference on single/dual-core machines can take 5–15 seconds per natural language query.
- **Status**: Implemented real-time UI system load indicator (`⚙️ Processing prompt... High CPU load expected`) and performance timing breakdown (`⚡ System Performance: Total X.Xs`).
- **Labels / Tags**: `Antigravity_generated`, `performance`, `p1`
- **Tracking**: [Issue #3: Local GGUF Model Inference Latency & System Load Reporting](https://github.com/sethusrinivasan/satellite-tracker/issues/3)

### 4. 🟡 [P2] High-Density SGP4 Propagation CPU Optimization
- **Summary**: SGP4 orbit propagation for country proximity search is computed in pure Python (`geo_query_service.py`). Scanning >20,000 active TLE records can take 1–2 seconds.
- **Mitigation**: Anomalous/decaying orbits are filtered out and LEO altitude bands are prioritized.
- **Labels / Tags**: `Antigravity_generated`, `performance`, `p2`
- **Tracking**: [Issue #4: Optimize Python SGP4 propagation with C-extensions / Numba batching](https://github.com/sethusrinivasan/satellite-tracker/issues/4)

---

## 🗺️ TODO Roadmap & Feature Backlog

- [ ] 🟡 **[P2] Dynamic System Prompt Configuration**: Allow administrators to edit few-shot SQL examples directly from the Admin Panel (`/admin`). (`Antigravity_generated`, `feature`, `p2`) ([Issue #5](https://github.com/sethusrinivasan/satellite-tracker/issues/5))
- [ ] 🟢 **[P3] Enhanced 3D WebGL Globe View**: Upgrade 2D/3D tracking interface with CesiumJS / Three.js for realistic Earth textures and orbital trajectory rendering. (`Antigravity_generated`, `frontend`, `p3`) ([Issue #6](https://github.com/sethusrinivasan/satellite-tracker/issues/6))
- [ ] 🟢 **[P3] TimescaleDB / PostgreSQL Driver Support**: Add configuration support for external PostgreSQL / TimescaleDB backends for historical TLE time-series storage. (`Antigravity_generated`, `database`, `p3`) ([Issue #7](https://github.com/sethusrinivasan/satellite-tracker/issues/7))

---

## 💬 Submitting Issues

When submitting new issues or reporting bugs:
1. Include the `Antigravity_generated` tag if generated during automated audits.
2. Use the provided [Bug Report Template](https://github.com/sethusrinivasan/satellite-tracker/issues/new?template=bug_report.md) or [Feature Request Template](https://github.com/sethusrinivasan/satellite-tracker/issues/new?template=feature_request.md).
