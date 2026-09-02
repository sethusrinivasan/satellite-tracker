# 📌 Known Issues & TODO Roadmap

This document tracks known issues, technical limitations, workarounds, and planned enhancement items for the **Satellite TLE Tracker & AI Orbital Discovery** platform.

To report new bugs or suggest features, please visit our **[GitHub Issues](https://github.com/sethusrinivasan/satellite-tracker/issues)** page.

---

## 🐛 Known Issues & Workarounds

### 1. Compact LLM Multi-Table JOIN Edge Cases
- **Description**: The 1.5B quantized model (`Qwen2.5-Coder-1.5B-Instruct-Q4_K_M`) translates most standard prompts into accurate SQL. However, for highly complex or ambiguous prompts, it may occasionally omit the `JOIN tle_elements` clause when referencing orbital parameters like `inclination_deg`.
- **Workaround**: System prompt few-shot examples guide the model toward proper `JOIN` syntax. For best results, include key terms in prompts (e.g. *"Show Starlink satellites with inclination > 53"*).
- **GitHub Tracking**: [Issue #1: Improve LLM SQL JOIN reasoning for complex multi-table queries](https://github.com/sethusrinivasan/satellite-tracker/issues/1)

### 2. High-Density SGP4 Propagation Memory Usage
- **Description**: SGP4 orbit propagation for country proximity search is computed in pure Python. Scanning large datasets exceeding 20,000 active TLE records can take 1–2 seconds on low-power hardware.
- **Workaround**: The application filters out decaying/anomalous TLE elements and caps results to LEO altitude bands by default.
- **GitHub Tracking**: [Issue #2: Optimize Python SGP4 propagation with C-extensions / Numba batching](https://github.com/sethusrinivasan/satellite-tracker/issues/2)

---

## 🗺️ TODO Roadmap & Future Enhancements

- [ ] **Dynamic System Prompt Configuration**: Allow administrators to edit few-shot SQL examples directly from the Admin Panel (`/admin`). ([Issue #3](https://github.com/sethusrinivasan/satellite-tracker/issues/3))
- [ ] **Enhanced 3D WebGL Globe View**: Upgrade the 2D/3D tracking interface with CesiumJS / Three.js for realistic Earth textures and orbital path trajectory rendering. ([Issue #4](https://github.com/sethusrinivasan/satellite-tracker/issues/4))
- [ ] **TimescaleDB / PostgreSQL Driver Support**: Add configuration support for external PostgreSQL / TimescaleDB backends for historical TLE time-series storage. ([Issue #5](https://github.com/sethusrinivasan/satellite-tracker/issues/5))
- [ ] **API Key Authentication**: Provide RESTful API key management for external automated satellite telemetry scripts. ([Issue #6](https://github.com/sethusrinivasan/satellite-tracker/issues/6))

---

## 💬 Submitting Issues

If you encounter a bug or have a feature request:
1. Check existing reports on **[GitHub Issues](https://github.com/sethusrinivasan/satellite-tracker/issues)**.
2. Use the provided [Bug Report Template](https://github.com/sethusrinivasan/satellite-tracker/issues/new?template=bug_report.md) or [Feature Request Template](https://github.com/sethusrinivasan/satellite-tracker/issues/new?template=feature_request.md).
