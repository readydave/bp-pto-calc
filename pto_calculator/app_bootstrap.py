from __future__ import annotations

import ctypes
import sys
from pathlib import Path

APP_NAME = "PTO Planner"
APP_ORGANIZATION_NAME = "PtoPlanner"
APP_DESKTOP_FILE_NAME = "pto-planner"
APP_BUNDLE_ID = "local.ptoplanner.app"


def package_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "pto_calculator"
    return Path(__file__).resolve().parent


def asset_path(*parts: str) -> Path:
    return package_root().joinpath("assets", *parts)


def app_icon_path() -> Path:
    return asset_path("pto-planner.png")


def ensure_windows_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_BUNDLE_ID)
    except (AttributeError, OSError):
        return
