# Security Policy

This project is an educational demonstration. Please still report issues that could expose admin access, mutate the datastore, or leak credentials.

## Supported versions

Security fixes land on the default branch. There is no long-term support window.

| Version | Supported |
| ------- | --------- |
| Default branch | Yes |
| Published container tags that match [`VERSION`](VERSION) | Best effort |
| Older forks / unpublished local copies | No |

## Reporting a vulnerability

Use [GitHub Security Advisories](https://github.com/sethusrinivasan/satellite-tracker/security/advisories/new) for anything that could grant admin access, run mutating SQL, or disclose secrets.

For non-sensitive bugs, open a [GitHub Issue](https://github.com/sethusrinivasan/satellite-tracker/issues).

Expect an acknowledgement within a few days. If the report is accepted, a fix will be discussed in the advisory before any public disclosure.

Do not include production secrets, OAuth client secrets, or live `instance/datastore.json` contents in issues.

## What is in scope

- Bypassing Google OAuth or `/auth/dev-bypass` outside native local development
- Executing mutating SQL through AI search or **Admin → Database**
- Reading or overwriting `instance/datastore.json`, `.env`, or uploaded TLE files without admin rights
- Container images that treat `RUNNING_IN_DOCKER=true` as local development

## Current controls

See [`docs/threat_model.md`](docs/threat_model.md) for the STRIDE matrix. High-level rules:

- `FLASK_ENV=production` (including the published `Dockerfile`) disables the local admin bypass even when `RUNNING_IN_DOCKER=true`.
- AI search and the admin SQL editor accept only a single `SELECT` / `WITH` / `EXPLAIN` statement and block mutation keywords.
- Engine choice lives in `instance/datastore.json`, not inside the satellite tables. Compose writes that file as the host user (`SATTRACK_UID` / `SATTRACK_GID`).
