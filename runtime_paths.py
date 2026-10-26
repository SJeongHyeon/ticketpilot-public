"""Locations for bundled application resources and per-user data."""

import os
from pathlib import Path
import sys


APP_NAME = "TicketPilot"
_PROJECT_ROOT = Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Return a path inside the source tree or PyInstaller bundle."""
    bundle_root = Path(getattr(sys, "_MEIPASS", _PROJECT_ROOT))
    return bundle_root.joinpath(*parts)


def user_data_path(*parts: str) -> Path:
    """Return a per-user TicketPilot path outside the installed bundle."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    base_directory = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base_directory.joinpath(APP_NAME, *parts)
