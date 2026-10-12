# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Determine repository root directory
_spec_dir = os.path.dirname(os.path.abspath(SPEC)) if "SPEC" in locals() else os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(_spec_dir, "app")):
    root_dir = _spec_dir
elif os.path.exists(os.path.join(_spec_dir, "..", "app")):
    root_dir = os.path.abspath(os.path.join(_spec_dir, ".."))
else:
    root_dir = os.getcwd()

datas = [
    (os.path.join(root_dir, 'app', 'templates'), 'app/templates'),
    (os.path.join(root_dir, 'app', 'static'), 'app/static'),
    (os.path.join(root_dir, 'data'), 'data'),
    (os.path.join(root_dir, 'VERSION'), '.'),
]

hiddenimports = [
    'config',
    'waitress',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.postgresql',
    'psycopg',
    'sqlite3',
    'authlib',
    'authlib.integrations.flask_client',
    'flask_login',
    'dotenv',
    'requests',
    'app',
    'app.routes.auth',
    'app.routes.upload',
    'app.routes.report',
    'app.routes.admin',
    'app.routes.setup',
    'app.services.datastore',
    'app.services.tle_parser',
    'app.services.geo_query_service',
    'app.services.query_cache',
    'app.services.demo_tle',
    'app.services.sql_console',
    'app.services.feature_flags',
    'app.services.ai_prompt_service',
    'app.services.city_temperature',
    'app.services.flight_overlay',
    'app.services.currency_overlay',
    'app.services.market_indices',
    'app.services.news_overlay',
    'app.services.shipping_overlay',
    'app.services.webcam_overlay',
    'app.services.world_events',
    'app.services.cloud_datacenters',
    'app.services.overlay_cache',
    'app.services.cache_backends',
    'app.services.overlay_http',
    'app.services.posthog',
]


try:
    import llama_cpp
    hiddenimports += collect_submodules('llama_cpp')
    datas += collect_data_files('llama_cpp')
except ImportError:
    pass

entry_file = os.path.join(root_dir, 'desktop', 'desktop_entry.py')
if not os.path.exists(entry_file):
    entry_file = os.path.join(root_dir, 'desktop_entry.py')

a = Analysis(
    [entry_file],
    pathex=[root_dir, os.path.join(root_dir, 'desktop')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='sattrack-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
