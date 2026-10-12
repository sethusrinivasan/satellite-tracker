#!/usr/bin/env python3
"""
Automated CycloneDX 1.5 Software Bill of Materials (SBOM) Generator.
Produces a machine-readable JSON inventory (docs/sbom.json) encompassing
Python backend dependencies, Tauri Node dependencies, and Rust crates.
Executes automatically on every build.
"""

from __future__ import annotations

import datetime
import importlib.metadata
import json
import os
import re
import uuid

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(ROOT_DIR, "docs", "sbom.json")
VERSION_FILE = os.path.join(ROOT_DIR, "VERSION")


def get_project_version() -> str:
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or "0.1.1"
    return "0.1.1"


def collect_python_components() -> list[dict]:
    """Extract installed Python packages specified in requirements.txt."""
    req_file = os.path.join(ROOT_DIR, "requirements.txt")
    components = []
    if not os.path.exists(req_file):
        return components

    with open(req_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    seen = set()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        pkg_name = re.split(r"[<>=;~]", line)[0].strip()
        if not pkg_name or pkg_name in seen:
            continue
        seen.add(pkg_name)

        version = "unknown"
        license_name = "Unknown"
        summary = ""
        try:
            dist = importlib.metadata.distribution(pkg_name)
            version = dist.version
            meta = dist.metadata
            summary = meta.get("Summary", "")
            license_name = meta.get("License", "Unknown") or "Unknown"
            if len(license_name) > 40:
                license_name = license_name.split()[0]
        except Exception:
            pass

        comp = {
            "type": "library",
            "name": pkg_name,
            "version": version,
            "purl": f"pkg:pypi/{pkg_name.lower()}@{version}",
            "description": summary or f"Python package {pkg_name}",
        }
        if license_name and license_name != "Unknown":
            comp["licenses"] = [{"license": {"name": license_name}}]
        components.append(comp)

    return components


def collect_node_components() -> list[dict]:
    """Extract npm devDependencies from package.json."""
    pkg_file = os.path.join(ROOT_DIR, "package.json")
    components = []
    if not os.path.exists(pkg_file):
        return components

    try:
        with open(pkg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for section in ["dependencies", "devDependencies"]:
            for name, ver in data.get(section, {}).items():
                clean_ver = ver.lstrip("^~>=")
                components.append({
                    "type": "library",
                    "name": name,
                    "version": clean_ver,
                    "purl": f"pkg:npm/{name}@{clean_ver}",
                    "description": f"Node.js package {name}",
                })
    except Exception:
        pass
    return components


def collect_rust_components() -> list[dict]:
    """Extract direct dependencies from Cargo.lock."""
    cargo_file = os.path.join(ROOT_DIR, "src-tauri", "Cargo.lock")
    components = []
    if not os.path.exists(cargo_file):
        return components

    try:
        with open(cargo_file, "r", encoding="utf-8") as f:
            content = f.read()
        packages = content.split("[[package]]")
        for pkg in packages:
            lines = [l.strip() for l in pkg.strip().splitlines() if l.strip()]
            pkg_data = {}
            for l in lines:
                if "=" in l:
                    k, v = l.split("=", 1)
                    pkg_data[k.strip()] = v.strip().strip('"')
            name = pkg_data.get("name")
            version = pkg_data.get("version")
            if name and version and name != "satellite-tracker":
                components.append({
                    "type": "library",
                    "name": name,
                    "version": version,
                    "purl": f"pkg:cargo/{name}@{version}",
                    "description": f"Rust crate {name}",
                })
    except Exception:
        pass
    return components[:50]  # Cap to top 50 direct crates to keep SBOM lean


def generate_sbom() -> str:
    version = get_project_version()
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    all_components = []
    all_components.extend(collect_python_components())
    all_components.extend(collect_node_components())
    all_components.extend(collect_rust_components())

    sbom = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": now_utc,
            "tools": [
                {
                    "vendor": "Antigravity",
                    "name": "CycloneDX Generator",
                    "version": "1.5.0",
                }
            ],
            "component": {
                "group": "sethusrinivasan",
                "name": "satellite-tracker",
                "version": version,
                "type": "application",
                "description": "Cross-Platform Real-Time Satellite TLE Tracker & AI Orbital Discovery",
                "licenses": [{"license": {"id": "MIT"}}],
            },
        },
        "components": all_components,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2)

    print(f"==> Generated CycloneDX 1.5 SBOM with {len(all_components)} components at: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    generate_sbom()
