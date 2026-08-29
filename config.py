"""Portable paths and FreeCAD preferences for the ASA Chain Drive Workbench."""

from __future__ import annotations

from pathlib import Path

import FreeCAD as App


PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/ASAChainDrive"


def preferences():
    return App.ParamGet(PREFERENCES_PATH)


def get_user_data_root(create=True):
    custom = preferences().GetString("UserDataPath", "").strip()
    freecad_data = Path(App.getUserAppDataDir())
    if freecad_data.name.lower().startswith("v"):
        freecad_data = freecad_data.parent
    root = (
        Path(custom).expanduser()
        if custom
        else freecad_data / "ASAChainDrive"
    )
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def get_sprocket_library_dir(create=True):
    custom = preferences().GetString("SprocketLibraryPath", "").strip()
    path = (
        Path(custom).expanduser()
        if custom
        else get_user_data_root(create=create) / "library" / "sprockets"
    )
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_output_dir(create=True):
    custom = preferences().GetString("OutputPath", "").strip()
    path = (
        Path(custom).expanduser()
        if custom
        else get_user_data_root(create=create) / "output"
    )
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_legacy_library_dirs(app_root):
    """Return development-era library locations that remain readable."""
    candidate = Path(app_root).resolve() / "output" / "sprockets"
    primary = get_sprocket_library_dir().resolve()
    if candidate.is_dir() and candidate.resolve() != primary:
        return [candidate]
    return []
