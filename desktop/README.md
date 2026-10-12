# Desktop Application

This directory contains the standalone cross-platform desktop application for **Satellite TLE Tracker & AI Orbital Discovery**, powered by **Tauri v2** (Rust) and an offline embedded Python backend sidecar compiled with **PyInstaller**.

---

## Architecture Overview

```
desktop/
├── desktop_entry.py     # Desktop runtime entrypoint (Waitress WSGI, dynamic port, AppData paths)
├── desktop.spec         # PyInstaller multi-platform compilation specification
├── src-tauri/           # Tauri v2 native desktop application wrapper (Rust)
│   ├── Cargo.toml       # Rust dependencies and configuration
│   ├── tauri.conf.json  # Tauri app window configuration, CSP, and bundle metadata
│   ├── src/             # Native window lifecycle, sidecar process supervisor (Rust)
│   ├── icons/           # App icons across Linux (.png), Windows (.ico), macOS (.icns)
│   └── binaries/        # Staged platform-specific sidecar binaries
└── README.md            # Architecture documentation and developer instructions
```

---

## How It Works

1. **Process Supervision**:
   - On application startup, the Tauri native host launches the PyInstaller-compiled `sattrack-backend` sidecar.
   - The sidecar binds to an ephemeral local port (`127.0.0.1:0`), initializes a dedicated local SQLite datastore in the user's OS AppData directory, and reports `READY:<port>` back to the Tauri host via stdout.
   - The Tauri webview loads `http://127.0.0.1:<port>` with hardware-accelerated WebGL rendering for 2D Leaflet and 3D Three.js orbital visualizers.

2. **Zero-Configuration Offline Storage**:
   - Platform-standard data locations:
     - **Linux**: `~/.local/share/satellite-tracker`
     - **macOS**: `~/Library/Application Support/satellite-tracker`
     - **Windows**: `%APPDATA%\satellite-tracker`
   - Cache and AI model locations:
     - **Linux**: `~/.cache/satellite-tracker/models`
     - **macOS**: `~/Library/Caches/satellite-tracker/models`
     - **Windows**: `%LOCALAPPDATA%\satellite-tracker\models`

---

## Development & Build Commands

Run all desktop commands from the repository root:

```bash
# Run desktop application in development mode
npm run desktop:dev

# Build Python sidecar and package native desktop installers
npm run desktop:build

# Build sidecar binary only
npm run build:sidecar
```

Or directly inside the `desktop/` directory:

```bash
cd desktop
npx tauri dev
npx tauri build
```
