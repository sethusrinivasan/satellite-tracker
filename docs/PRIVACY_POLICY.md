# Privacy Policy for Satellite TLE Tracker

**Last updated: October 2026**

Satellite TLE Tracker ("the Application") is built as a privacy-first, offline-capable mobile and desktop utility. This document describes our commitments regarding data collection, privacy, and security.

---

### 1. Zero Tracking & No Account Requirement
- The Application requires **no user registration or account creation**.
- We do **not** collect, store, sell, or share personal identifying information (PII).
- We do **not** integrate third-party analytics trackers, advertising SDKs, or behavioral profiling tools.

---

### 2. Location Data (GPS)
- **Observer Location**: The Application may request access to your device's coarse or precise location exclusively to calculate local satellite overpasses (Acquisition of Signal, maximum elevation above your horizon, and sky compass direction).
- Location data is processed **strictly on-device**.
- Your coordinates are **never transmitted** to our servers or any third-party services.
- You can manually enter custom coordinates at any time without granting device location permissions.

---

### 3. Ephemeris & Telemetry Feeds
- When you refresh satellite data, the Application makes direct HTTPS GET requests to public ephemeris repositories (such as CelesTrak.org) to obtain the latest Two-Line Element (TLE) ephemeris data.
- Downloaded TLE data is cached locally in device storage (IndexedDB / localStorage) to enable full offline functionality.

---

### 4. Optional Remote AI Features & API Key Security
- The Application includes an optional natural language orbital query assistant.
- **Optional Feature**: If you do not configure an AI provider, the Application functions 100% locally using built-in catalog search and orbital math.
- **Provider Keys**: If you choose to configure a key for Google Gemini, OpenAI, Anthropic, or a custom endpoint:
  - Your API key is stored **exclusively in your device's local storage**.
  - The Application never transmits your API key to any intermediary proxy or third-party server.
  - Queries are sent directly from your device to the designated AI provider endpoint over encrypted HTTPS.
  - Please review your chosen AI provider's privacy policy for details on their data handling practices.

---

### 5. Data Safety Summary (Google Play & Amazon)
| Category | Collected? | Shared? | Purpose |
| :--- | :--- | :--- | :--- |
| **Personal Info (Name, Email)** | No | No | N/A |
| **Location Data** | Ephemeral, on-device only | No | Local overpass calculations |
| **Financial / Payment Info** | No | No | N/A |
| **Health / Fitness** | No | No | N/A |
| **Photos / Media / Files** | No | No | N/A |
| **App Activity / Analytics** | No | No | N/A |
| **Device IDs** | No | No | N/A |

---

### 6. Contact & Questions
For any questions regarding this Privacy Policy, please contact:
- **Repository**: [https://github.com/sethusrinivasan/satellite-tracker](https://github.com/sethusrinivasan/satellite-tracker)
- **Author**: Sethu Srinivasan
