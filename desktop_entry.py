#!/usr/bin/env python3
"""
Desktop entrypoint proxy for Satellite TLE Tracker.
Delegates to desktop/desktop_entry.py for clean repository structure.
"""

from __future__ import annotations

import os
import sys

_desktop_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "desktop")
if _desktop_dir not in sys.path:
    sys.path.insert(0, _desktop_dir)

from desktop.desktop_entry import (
    ensure_desktop_environment,
    find_free_port,
    get_default_desktop_data_dir,
    get_default_desktop_model_dir,
    handle_shutdown,
    main,
)

if __name__ == "__main__":
    main()
