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
   - Quick navigation links (`Search / Discovery`, `Batch Upload`, `Statistics`, `Admin Panel`).
   - Active route detection & indicator styling.
2. **Tabbed Search Layout**:
   - **🔍 Keyword Search**: Fast instantaneous search by satellite name or NORAD catalog ID.
   - **🌍 Country Proximity Search**: Orbit propagation computing the 15 closest satellites to a chosen country.
   - **💬 AI Search**: Conversational natural-language search with executed SQL preview.
3. **Interactive Results Table**:
   - Batch selection checkboxes with floating action bar ("Track Selected 🛰️").
   - Inline status classification badges (`U` = Unclassified, `C` = Classified, `S` = Secret).
4. **Interactive 2D/3D Globe Tracker**:
   - Real-time SGP4 propagation updating satellite coordinates every second.
   - Ground track projections, latitude/longitude overlay, and orbital altitude stats.

---

## 3. Micro-Interactions & UX Polish

- **Feedback Animations**: Smooth spinners during background AI inference and orbit calculations.
- **Glassmorphism**: Soft background blur (`backdrop-filter: blur(12px)`) on modals and cards.
- **Responsive Adaptability**: Flexbox & CSS Grid layouts scaling from desktop displays to mobile screens.
- **SQL Transparency**: The AI search panel displays the generated SQL query in a syntax-highlighted visualizer block, giving users complete transparency into how their question was converted to SQL.
