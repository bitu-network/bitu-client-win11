# file: src/lib/drives.py
# description: drive enumeration and per-drive BITU config validation, shared by
# cli/start.py (to decide which drives get a file_server.py spawned) and
# service/file_server.py (to load its own config once launched).

from __future__ import annotations

import json
import string
import sys
from pathlib import Path

CONFIG_REL_PATH = Path("I") / "-" / "bitu" / "config.json"

# Required keys for a config to be considered valid enough to start a file_server for.
REQUIRED_CONFIG_KEYS = ("port",)


def enumerate_drive_roots() -> list[Path]:
    """Return all currently mounted drive roots. Windows only."""
    if sys.platform != "win32":
        return []
    import ctypes

    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    roots = []
    for i, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << i):
            roots.append(Path(f"{letter}:\\"))
    return roots


def load_drive_config(drive_root: Path) -> dict | None:
    """Load and validate <drive>:\\I\\-\\bitu\\config.json.

    Returns the parsed config dict if it exists and has the required keys,
    otherwise None. The absence of a valid config is the intended mechanism
    for opting a drive out of running a file_server -- not an error.
    """
    config_path = drive_root / CONFIG_REL_PATH
    try:
        if not config_path.is_file():
            return None
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # OSError covers unready/removed media (e.g. an empty optical drive);
        # ValueError covers malformed JSON. Both mean "treat as absent".
        return None

    if not isinstance(data, dict):
        return None
    if not all(key in data for key in REQUIRED_CONFIG_KEYS):
        return None
    return data


def find_bitu_drives() -> list[tuple[Path, dict]]:
    """Return (drive_root, config) for every currently mounted drive that has
    a valid BITU config -- i.e. every drive that should get a file_server."""
    result = []
    for root in enumerate_drive_roots():
        config = load_drive_config(root)
        if config:
            result.append((root, config))
    return result
