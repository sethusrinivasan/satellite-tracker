# 🛡️ Satellite Tracker Threat Model

This document outlines the security architecture, risk analysis, and threat mitigations for the **Satellite TLE Tracker & AI Orbital Discovery** platform. The threat analysis follows the **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).

---

## 1. System Boundaries & Assets

### Key Assets
1. **Active datastore** (SQLite under `instance/` or PostgreSQL): satellite records, TLE state vectors, upload history, and `saved_queries`.
2. **Datastore config** (`instance/datastore.json`): engine, URI, and credentials for the chosen backend. Not stored inside the satellite tables.
3. **Offline LLM Engine** (`app/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`): In-process local GGUF model binary.
4. **Admin Panel Credentials & OAuth Tokens**: Google OAuth2 client secrets and session cookies.
5. **Web analytics (optional PostHog)**: Pageviews and autocapture go to your PostHog project when `POSTHOG_PROJECT_API_KEY` is set. Session replay is off unless `POSTHOG_SESSION_REPLAY=true`.

### Trust Boundaries
- **User Client Interface (Browser)** $\rightarrow$ **Public API Endpoints** (`/report`, `/tracker`, `/api/natural-query`, `/api/geo-query`, `/api/proximity/options`, `/upload`).
- **Authenticated Admin User** $\rightarrow$ **Admin Management API** (`/admin/*`, `/admin/database/*`, `/auth/*`).
- **Unauthenticated first launch** $\rightarrow$ **`/setup`** (only while `DATASTORE_CONFIGURED` is false).
- **Flask Process** $\rightarrow$ **Local File System, SQLite file, or PostgreSQL**.

---

## 2. STRIDE Risk Categorization Matrix

| Threat ID | STRIDE Category | Risk Description | Severity | Mitigating Security Control | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TM-01** | **Tampering / Injection** | **SQL Injection / DB Mutation via Natural Query**<br>Attacker attempts prompt injection to inject `DROP TABLE`, `UPDATE`, or `DELETE` commands into Text-to-SQL. | **Critical** | `validate_sql_safety()` enforces read-only policy. Only statements starting with `SELECT` are permitted. Blocklist regex blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `PRAGMA`, `ATTACH`, `DETACH`. | **Mitigated** |
| **TM-01b** | **Tampering / Injection** | **Admin SQL editor mutation**<br>Authenticated admin pastes stacked or mutating SQL into `/admin/database`. | **High** | `validate_readonly_sql()` allows one `SELECT` / `WITH` / `EXPLAIN`, rejects `;` stacks and the same mutation blocklist. Row cap 1–10 000. | **Mitigated** |
| **TM-02** | **Spoofing** | **Unauthorized Admin Access**<br>Unauthenticated user attempts to access administrative functions (`/admin/reset`, `/admin/delete`). | **High** | Protected by `@admin_required` decorator integrated with Google OAuth2. Optional email allowlist via `ADMIN_ALLOWED_EMAILS`. | **Mitigated** |
| **TM-02b** | **Elevation of Privilege** | **Local admin bypass on cloud/Docker**<br>`/auth/dev-bypass` reachable because the process is in a container. | **Critical** | `is_local_dev()` returns false when `FLASK_ENV=production`. `RUNNING_IN_DOCKER` is not treated as local. Bypass only on localhost/dev. | **Mitigated** |
| **TM-03** | **Information Disclosure** | **Secret & Credentials Leakage**<br>OAuth secrets or database binary checked into public version control. | **High** | Credentials externalized to environment variables (`.env`). `.gitignore` excludes `.env`, `instance/*.db`, `instance/datastore.json`, and `app/models/*.gguf`. | **Mitigated** |
| **TM-03b** | **Information Disclosure** | **Unreadable datastore.json treated as first-launch**<br>`Permission denied` on `instance/datastore.json` sent users through `/setup` and could overwrite a live engine. | **High** | Unreadable existing file is `DATASTORE_UNREADABLE`, not unconfigured. Compose uses host UID/GID; root processes repair ownership. | **Mitigated** |
| **TM-04** | **Denial of Service** | **LLM Memory & CPU Exhaustion**<br>Simultaneous heavy natural language queries overwhelm local CPU/RAM during GGUF inference. | **Medium** | Single-instance lazy loading of `Llama` model with thread locks (`n_threads=4`, `n_ctx=2048`). Model context window capped to prevent memory buffer overflow. | **Mitigated** |
| **TM-05** | **Tampering** | **Malicious File Upload Payload**<br>User uploads corrupted or excessively large TLE files to overwhelm disk space or parser memory. | **Medium** | Flask `MAX_CONTENT_LENGTH` enforced at 16MB. TLE line parser performs strict line-length checks and checksum validation prior to DB commit. | **Mitigated** |
| **TM-06** | **Elevation of Privilege** | **Prompt Injection Schema Bypass**<br>Attacker crafts prompt to trick LLM into revealing system database tables or unmapped metadata. | **Low** | System prompt scopes LLM knowledge strictly to `satellites` and `tle_elements` tables. Post-generation query parser extracts only valid `norad_cat_id` catalog integer outputs. | **Mitigated** |
| **TM-07** | **Denial of Service** | **Concurrent Model Download Thread Exhaustion**<br>Attacker triggers multiple concurrent download requests for the 900MB GGUF model file. | **Low** | Download thread managed via mutex lock (`threading.Lock()`). Endpoint returns `already downloading` status if download worker is active. | **Mitigated** |
| **TM-08** | **Information Disclosure / SSRF** | **Tracker overlay proxies**<br>Weather, markets, currencies, flights, news, ships, webcams, city temperatures, and cloud datacenters call third-party APIs. A crafted request could try to forward user text or open an internal URL. | **Medium** | Overlay routes are read-only GET proxies with fixed provider URLs. They do not forward search text. News uses a fixed highlight query. Webcam URLs must be `http`/`https`. Cloud DC pings use a hardcoded HTTPS catalog. Shared cache with per-feed TTL plus host backoff on `429`/`Retry-After` reduces repeat fetches. | **Mitigated** |

---

## 3. Detailed Threat Mitigations

### 3.1 Text-to-SQL Safety Validation (`TM-01`)
Every SQL query generated by the local GGUF model is passed through `validate_sql_safety()` prior to execution:

```python
def validate_sql_safety(sql: str) -> bool:
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        return False
    blocklist = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "PRAGMA", "GRANT", "SHUTDOWN", "ATTACH", "DETACH"]
    for keyword in blocklist:
        if re.search(r'\b' + keyword + r'\b', sql_upper):
            return False
    return True
```

Admin SQL uses `app/services/sql_console.py` (`validate_readonly_sql`) which also rejects stacked statements.

### 3.2 Production auth fail-closed (`TM-02b`)
The published `Dockerfile` sets `FLASK_ENV=production` and `RUNNING_IN_DOCKER=true`. `is_local_dev()` must not treat Docker as local. Compose local profiles set `FLASK_ENV=development` but still do not expose bypass unless the request host is localhost.

### 3.3 Air-Gapped Offline Execution (`TM-03`, `TM-04`)
The LLM inference pipeline runs entirely in-process using `llama-cpp-python`. No user queries or prompt data are transmitted to external LLM provider API endpoints over the internet, ensuring zero external data exposure.

---

## 4. Security Audit & Compliance Checklist

- [x] **No hardcoded secrets** in source code repositories.
- [x] **Input validation** on all uploaded files and query inputs.
- [x] **Session security** using signed Flask cookies (`SECRET_KEY`).
- [x] **Read-only query enforcement** on natural language search routes **and** admin SQL explorer.
- [x] **Local admin bypass disabled** in `FLASK_ENV=production`.
- [x] **Comprehensive `.gitignore`** protecting sensitive instance storage including `datastore.json`.
