# file: src/lib/config.py
# description: centralizes everything about the per-drive BITU config file --
# its location, schema (required/optional keys, defaults), and load/validation
# logic. Other modules (lib/drives.py, service/dedupe.py, server/file_server.py,
# cli/*.py) read config through this module rather than parsing config.json
# themselves, so a new field only needs to be understood in one place.

from __future__ import annotations

import json
from pathlib import Path

CONFIG_REL_PATH = Path("I") / "-" / "bitu" / "config.json"

# Keys a config.json must have to be considered valid enough to opt a drive in.
REQUIRED_KEYS = ("port",)

# Optional keys and their defaults, merged into a valid config after loading.
# (Empty for now -- "port" is currently the only field. Add entries here as
# optional fields are introduced, e.g. {"peer_allowlist": []}.)
DEFAULT_VALUES: dict = {}


def config_path(drive_root: Path) -> Path:
    """<drive>:\\I\\-\\bitu\\config.json for a given drive root."""
    return drive_root / CONFIG_REL_PATH


def load_drive_config(drive_root: Path) -> dict | None:
    """Load, validate, and apply defaults to a drive's config.json.

    Returns None if the file is missing, unreadable, malformed, or missing a
    required key. That's the intended mechanism for opting a drive out of
    running BITU services -- not an error condition.
    """
    path = config_path(drive_root)
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # OSError covers unready/removed media (e.g. an empty optical drive);
        # ValueError covers malformed JSON. Both mean "treat as absent".
        return None

    if not isinstance(data, dict):
        return None
    if not all(key in data for key in REQUIRED_KEYS):
        return None

    return {**DEFAULT_VALUES, **data}
