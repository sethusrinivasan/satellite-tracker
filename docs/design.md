# 🎨 Satellite Tracker Design System & UI/UX Guidelines

This document outlines the visual design system, UI components, responsive layout strategy, and user experience decisions for the **Satellite TLE Tracker & AI Orbital Discovery** platform.

---

## 1. Design Aesthetic & Color Palette

The interface utilizes a sleek **glassmorphic dark theme** tailored for space monitoring and orbital telemetry visualization.

### Color Tokens

| Token | Hex / Value | Application |
| :--- | :--- | :--- |
| `--bg` | `#0b0f19` | Deep space background |
| `--bg-card` | `rgba(17, 24, 39, 0.8)` | Glassmorphic card surfaces |
| `--border` | `rgba(255, 255, 255, 0.08)` | Subtle card & tab borders |
| `--accent` | `#3b82f6` / `#60a5fa` | Vibrant electric blue primary highlight |
| `--accent-glow` | `rgba(59, 130, 246, 0.25)` | Micro-interaction focus states & glows |
| `--success` | `#10b981` | Positive status, valid SQL query execution |
| `--warning` | `#f59e0b` | Warnings, missing AI model prompt |
| `--error` | `#ef4444` | Errors, security blocked queries |
| `--text` | `#f3f4f6` | High-contrast body & header text |
| `--text-muted` | `#9ca3af` | Secondary labels, descriptions, units |

---

## 2. Navigation & View Hierarchy

1. **Top Navbar**:
   - Brand identity with live satellite icon animation.
   - Quick navigation links (`Search`, `Upload`, `Statistics`, `Admin`).
   - Upload points at `upload.upload_file` (`GET /upload`), not the home redirect.
   - Active route detection & indicator styling.
2. **First-launch `/setup`**:
   - Single-purpose wizard to pick SQLite or PostgreSQL before any other page.
   - Same field partial (`_datastore_form.html`) is reused on Admin → Database.
3. **Tabbed Search layout** (`/report`):
   - **Keyword Search (default)**: Instant list. Empty query is a wildcard (all records). Typed query `ILIKE`s any satellite/TLE text field.
   - **Country Proximity Search**: Dropdown of countries that have geo reference data; prefix table from the first word of each satellite name; click a prefix to filter the proximity run.
   - **AI Search**: Conversational natural-language search with executed SQL preview.
4. **Interactive Results Table**:
   - Batch selection checkboxes with floating action bar ("Track Selected 🛰️").
   - Inline status classification badges (`U` = Unclassified, `C` = Classified, `S` = Secret).
5. **Interactive 2D/3D Globe Tracker & satellite detail map**:
   - Real-time SGP4 updates every second.
   - Default basemap is Esri World Dark Gray (no key). Optional CARTO dark tiles when `CARTO_API_KEY` is set.
   - **Full screen** expands the map card/shell as a fixed overlay; **Exit full screen** or Escape restores the layout and Leaflet `invalidateSize` is called.
   - Optional **Weather & quakes** checkbox overlays NASA EONET weather/climate events (storms, floods, droughts, ice, temperature extremes, wildfires), USGS M4.5+ earthquakes, and Open-Meteo temperature pins for cities over 1 million people. Earthquake bubbles scale radius and color by magnitude (yellow → orange → red → maroon). City pins show the latest daily mean and 7d / 30d / 90d / 1y °C change. Off by default.
   - Optional **Markets** checkbox pins major world indexes. Pin color is the 1-day CNBC change (green/red). Tooltip shows the index level plus 1d / 7d / 30d / 1q / 6m / 1y / 2y / 5y / 10y % (longer horizons from Yahoo daily closes).
   - Optional **Currencies** checkbox pins major currencies. The popup lists how many local units buy 1 USD, 1 EUR, 1 yen, 1 oz gold, 1 barrel of WTI, and 1 Big Mac, plus 1d / 7d / 30d / 90d / 6m / 1y / 5y % for FX and gold.
   - Optional **Flights** checkbox pins airborne aircraft from The OpenSky Network in the current view (heading-rotated markers; refreshes about every 20s).
   - Optional **News** checkbox pins last-24h GDACS alerts plus UN News, Global Voices, The Conversation, and Deutsche Welle headlines. Pins use published coordinates or a gazetteer match. Hover shows a short title; click opens the article (`target="_blank"`).
   - Optional **Ships** checkbox loads current AIS positions from Fintraffic Digitraffic (Finland/Baltic, CC BY 4.0). Hover a vessel for its latest location and timestamp.
   - Optional **Webcams** checkbox pins official public camera pages worldwide plus OpenStreetMap cams around world hubs and when zoomed in. Hover shows the title; click the title to open the publisher page in a new tab.
   - Optional **Cloud DCs** checkbox pins AWS (orange), Azure (blue), and GCP (green) regions. Hover shows HTTPS ping p50 / p95 / p99 from this SatTrack server.
   - A map credit strip plus popup footnotes attribute Esri, NASA EONET, USGS, Open-Meteo, CNBC, Yahoo Finance, Frankfurter, The Economist Big Mac Index, OpenSky, adsbdb, GDACS, UN News, Global Voices, The Conversation, Deutsche Welle, Fintraffic Digitraffic, AWS, Azure, and Google Cloud. Overlay data is free/public only.
6. **Admin Database explorer** (`/admin/database`):
   - Table list with row counts and a one-click `SELECT` load.
   - SQL editor with max-rows cap, result grid, elapsed time / rows-per-sec, CSV and Excel export.
   - Saved queries sidebar (name, last row count, p50/p95/p99/p100) stored in the active database.

---

## 3. Micro-Interactions & UX Polish

- **Feedback Animations**: Smooth spinners during background AI inference and orbit calculations.
- **Glassmorphism**: Soft background blur (`backdrop-filter: blur(12px)`) on modals and cards.
- **Responsive Adaptability**: Flexbox & CSS Grid layouts scaling from desktop displays to mobile screens. Tracker `.map-layout` is `1fr 280px` until fullscreen.
- **SQL Transparency**: The AI search panel and the admin SQL explorer both show the statement that ran, plus timing badges.
