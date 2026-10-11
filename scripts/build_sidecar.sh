#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -d "${ROOT_DIR}/venv" ]; then
    exec "${ROOT_DIR}/venv/bin/python3" "${ROOT_DIR}/scripts/build_sidecar.py"
else
    exec python3 "${ROOT_DIR}/scripts/build_sidecar.py"
fi
