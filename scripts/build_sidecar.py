#!/usr/bin/env python3
"""
Cross-platform sidecar builder for Satellite TLE Tracker & AI Orbital Discovery.
Works seamlessly across Windows, macOS, and Linux runners.
Compiles desktop_entry.py using PyInstaller and places the resulting executable
into src-tauri/binaries/ with the appropriate target triple name.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys


def detect_target_triple() -> str:
    """Detect rust target triple from rustc or fallback to platform heuristics."""
    try:
        res = subprocess.run(
            ["rustc", "-vV"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        for line in res.stdout.splitlines():
            if line.startswith("host:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass

    machine = platform.machine().lower()
    system = platform.system().lower()

    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    arch = arch_map.get(machine, machine)

    if system == "linux":
        return f"{arch}-unknown-linux-gnu"
    elif system == "darwin":
        return f"{arch}-apple-darwin"
    elif system == "windows":
        return f"{arch}-pc-windows-msvc"
    return f"{arch}-unknown-{system}"


def main() -> None:
    target_triple = detect_target_triple()
    print(f"==> Detected Rust target triple: {target_triple}")

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)

    # Ensure every new build updates and synchronizes project version
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    if "--no-bump" not in sys.argv and os.getenv("SKIP_VERSION_BUMP") != "1":
        try:
            from bump_version import bump_version, get_current_version
            old_ver = get_current_version(root_dir)
            new_ver = bump_version(bump_type="patch", root_dir=root_dir)
            print(f"==> Updated build version for new build: {old_ver} -> {new_ver}")
        except Exception as exc:
            print(f"Warning: Could not auto-bump version: {exc}", file=sys.stderr)

    # Regenerate CycloneDX SBOM on every build
    try:
        from generate_sbom import generate_sbom
        generate_sbom()
    except Exception as exc:
        print(f"Warning: Could not auto-generate SBOM: {exc}", file=sys.stderr)

    is_windows = sys.platform.startswith("win")
    exe_suffix = ".exe" if is_windows else ""

    spec_file = os.path.join("desktop", "desktop.spec")
    if not os.path.exists(spec_file):
        spec_file = "desktop.spec"
    if not os.path.exists(spec_file):
        print(f"ERROR: spec file not found in desktop/ or {root_dir}", file=sys.stderr)
        sys.exit(1)

    has_uv = shutil.which("uv") is not None
    if has_uv:
        print("==> Building sidecar using uv and PyInstaller...")
        cmd = [
            "uv", "run",
            "--with", "pyinstaller",
            "--with", "waitress",
            "--with-requirements", "requirements.txt",
            "pyinstaller", "--noconfirm", spec_file,
        ]
        subprocess.run(cmd, check=True)
    else:
        print("==> Verifying build dependencies (pyinstaller, waitress)...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "pyinstaller", "waitress"],
                check=True,
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "pyinstaller", "waitress"],
                check=True,
            )

        print(f"==> Running PyInstaller with spec: {spec_file}...")
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file],
            check=True,
        )


    src_binary = os.path.join("dist", f"sattrack-backend{exe_suffix}")
    if not os.path.isfile(src_binary):
        print(f"ERROR: Expected binary at {src_binary} was not found!", file=sys.stderr)
        sys.exit(1)

    target_dirs = [
        os.path.join("desktop", "src-tauri", "binaries"),
        os.path.join("src-tauri", "binaries"),
    ]
    seen_dirs = set()
    for b_dir in target_dirs:
        real_b_dir = os.path.realpath(b_dir)
        if real_b_dir in seen_dirs:
            continue
        seen_dirs.add(real_b_dir)
        os.makedirs(b_dir, exist_ok=True)

        dest_triple_binary = os.path.join(
            b_dir, f"sattrack-backend-{target_triple}{exe_suffix}"
        )
        shutil.copy2(src_binary, dest_triple_binary)
        if not is_windows:
            os.chmod(dest_triple_binary, 0o755)

        print(f"==> Successfully staged sidecar binary: {dest_triple_binary}")

        dest_standard_binary = os.path.join(b_dir, f"sattrack-backend{exe_suffix}")
        shutil.copy2(src_binary, dest_standard_binary)
        if not is_windows:
            os.chmod(dest_standard_binary, 0o755)


if __name__ == "__main__":
    main()
