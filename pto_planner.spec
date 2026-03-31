# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


PROJECT_ROOT = Path(SPEC).resolve().parent
APP_NAME = "PTO Planner"
APP_BUNDLE_ID = "local.ptoplanner.app"
ICON_DIR = PROJECT_ROOT / "pto_calculator" / "assets"


def read_version() -> str:
    package_init = PROJECT_ROOT / "pto_calculator" / "__init__.py"
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', package_init.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError("Unable to determine the PTO Planner version.")
    return match.group(1)


APP_VERSION = read_version()
PACKAGE_DATA = collect_data_files("pto_calculator", includes=["assets/*"])
EXE_ICON = None
if sys.platform == "win32":
    EXE_ICON = str(ICON_DIR / "pto-planner.ico")
elif sys.platform == "darwin":
    EXE_ICON = str(ICON_DIR / "pto-planner.icns")


a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=PACKAGE_DATA,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=EXE_ICON,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=str(ICON_DIR / "pto-planner.icns"),
        bundle_identifier=APP_BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            "CFBundleDisplayName": APP_NAME,
            "CFBundleName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
        },
    )
