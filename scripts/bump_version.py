#!/usr/bin/env python3
"""
Automated Version Management Utility for Satellite TLE Tracker.
Ensures every new build increments and synchronizes version across all project files:
  - VERSION
  - package.json
  - src-tauri/tauri.conf.json
  - src-tauri/Cargo.toml
  - README.md
  - docs/index.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Optional


def get_project_root() -> str:
    """Return repository root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_current_version(root_dir: Optional[str] = None) -> str:
    """Read the current canonical version from VERSION file."""
    root = root_dir or get_project_root()
    version_file = os.path.join(root, "VERSION")
    if os.path.exists(version_file):
        with open(version_file, "r", encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    return "0.1.0"


def bump_semver(version: str, part: str = "patch") -> str:
    """Increment semver version string (major, minor, or patch)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", version.strip())
    if not match:
        raise ValueError(f"Invalid semver version format: {version}")

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    suffix = match.group(4)

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown version bump part: {part} (use major, minor, or patch)")

    return f"{major}.{minor}.{patch}{suffix}"


def update_all_files(root_dir: str, new_version: str, dry_run: bool = False) -> list[str]:
    """Synchronize the new version across all project configuration files."""
    updated: list[str] = []

    # 1. VERSION
    version_file = os.path.join(root_dir, "VERSION")
    if not dry_run:
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(f"{new_version}\n")
    updated.append("VERSION")

    # 2. package.json
    pkg_file = os.path.join(root_dir, "package.json")
    if os.path.exists(pkg_file):
        with open(pkg_file, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        pkg["version"] = new_version
        if not dry_run:
            with open(pkg_file, "w", encoding="utf-8") as f:
                json.dump(pkg, f, indent=2)
                f.write("\n")
        updated.append("package.json")

    # 3. desktop/src-tauri/tauri.conf.json
    tauri_file = os.path.join(root_dir, "desktop", "src-tauri", "tauri.conf.json")
    if not os.path.exists(tauri_file):
        tauri_file = os.path.join(root_dir, "src-tauri", "tauri.conf.json")
    if os.path.exists(tauri_file):
        with open(tauri_file, "r", encoding="utf-8") as f:
            tauri_cfg = json.load(f)
        tauri_cfg["version"] = new_version
        if not dry_run:
            with open(tauri_file, "w", encoding="utf-8") as f:
                json.dump(tauri_cfg, f, indent=2)
                f.write("\n")
        updated.append("desktop/src-tauri/tauri.conf.json")

    # 4. desktop/src-tauri/Cargo.toml
    cargo_file = os.path.join(root_dir, "desktop", "src-tauri", "Cargo.toml")
    if not os.path.exists(cargo_file):
        cargo_file = os.path.join(root_dir, "src-tauri", "Cargo.toml")
    if os.path.exists(cargo_file):
        with open(cargo_file, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(
            r'(^\[package\][\s\S]*?\nversion\s*=\s*")[^"]+(")',
            rf"\g<1>{new_version}\g<2>",
            content,
            count=1,
        )
        if not dry_run:
            with open(cargo_file, "w", encoding="utf-8") as f:
                f.write(new_content)
        updated.append("src-tauri/Cargo.toml")

    # 5. README.md badges
    readme_file = os.path.join(root_dir, "README.md")
    if os.path.exists(readme_file):
        with open(readme_file, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(
            r'version-\d+\.\d+\.\d+-blue\.svg',
            f"version-{new_version}-blue.svg",
            content,
        )
        if not dry_run:
            with open(readme_file, "w", encoding="utf-8") as f:
                f.write(new_content)
        updated.append("README.md")

    # 6. docs/index.md badges
    docs_file = os.path.join(root_dir, "docs", "index.md")
    if os.path.exists(docs_file):
        with open(docs_file, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(
            r'version-\d+\.\d+\.\d+-blue\.svg',
            f"version-{new_version}-blue.svg",
            content,
        )
        if not dry_run:
            with open(docs_file, "w", encoding="utf-8") as f:
                f.write(new_content)
        updated.append("docs/index.md")

    return updated


def check_version_sync(root_dir: str) -> tuple[bool, dict[str, str]]:
    """Check if all project files have synchronized versions."""
    root = root_dir or get_project_root()
    versions: dict[str, str] = {}

    v_file = os.path.join(root, "VERSION")
    if os.path.exists(v_file):
        with open(v_file, "r", encoding="utf-8") as f:
            versions["VERSION"] = f.read().strip()

    pkg_file = os.path.join(root, "package.json")
    if os.path.exists(pkg_file):
        with open(pkg_file, "r", encoding="utf-8") as f:
            versions["package.json"] = json.load(f).get("version", "")

    tauri_file = os.path.join(root, "desktop", "src-tauri", "tauri.conf.json")
    if not os.path.exists(tauri_file):
        tauri_file = os.path.join(root, "src-tauri", "tauri.conf.json")
    if os.path.exists(tauri_file):
        with open(tauri_file, "r", encoding="utf-8") as f:
            versions["tauri.conf.json"] = json.load(f).get("version", "")

    cargo_file = os.path.join(root, "desktop", "src-tauri", "Cargo.toml")
    if not os.path.exists(cargo_file):
        cargo_file = os.path.join(root, "src-tauri", "Cargo.toml")
    if os.path.exists(cargo_file):
        with open(cargo_file, "r", encoding="utf-8") as f:
            m = re.search(r'version\s*=\s*"([^"]+)"', f.read())
            if m:
                versions["Cargo.toml"] = m.group(1)

    unique_versions = set(versions.values())
    is_synced = len(unique_versions) == 1
    return is_synced, versions


def bump_version(
    bump_type: str = "patch",
    set_version: Optional[str] = None,
    root_dir: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """Core function to bump and sync versions across project."""
    root = root_dir or get_project_root()
    current = get_current_version(root)

    if set_version:
        new_version = set_version.strip().lstrip("v")
    else:
        new_version = bump_semver(current, part=bump_type)

    update_all_files(root, new_version, dry_run=dry_run)
    return new_version


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize and increment version across all Satellite Tracker files for new builds."
    )
    parser.add_argument(
        "--type",
        choices=["patch", "minor", "major"],
        default="patch",
        help="Part of semver to increment (default: patch)",
    )
    parser.add_argument(
        "--set",
        dest="set_version",
        type=str,
        default=None,
        help="Explicitly set a specific version string (e.g. 0.2.0)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify whether all project files have synchronized version numbers",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display computed version changes without modifying files",
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Print current canonical version and exit",
    )
    args = parser.parse_args()

    root = get_project_root()

    if args.current:
        print(get_current_version(root))
        return

    if args.check:
        synced, versions = check_version_sync(root)
        print("Version synchronization status:")
        for file_name, ver in versions.items():
            print(f"  - {file_name}: {ver}")
        if synced:
            print("==> All version declarations are in sync.")
            sys.exit(0)
        else:
            print("ERROR: Version declarations are out of sync!", file=sys.stderr)
            sys.exit(1)

    old_version = get_current_version(root)
    new_version = bump_version(
        bump_type=args.type,
        set_version=args.set_version,
        root_dir=root,
        dry_run=args.dry_run,
    )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"==> {prefix}Updated project version: {old_version} -> {new_version}")


if __name__ == "__main__":
    main()
