# file: src/pod/config.py
# description: centralizes everything about the per-drive BITU config file --
# its location, schema (required/optional keys, defaults), and load/validation
# logic. Other modules (pod/drives.py, service/dedupe.py, server/file_server.py,
# cli/*.py) read config through this module rather than parsing config.json
# themselves, so a new field only needs to be understood in one place.

from __future__ import annotations

import json
from pathlib import Path

from .paths import PERSONAL_CONCEPTS_DIR, pod_root

CONFIG_REL_PATH = Path(PERSONAL_CONCEPTS_DIR) / "bitu" / "config.json"  # I\-\bitu\config.json

# Keys a config.json must have to be considered valid enough to opt a drive in.
REQUIRED_KEYS = ("base_port",)

# Every per-drive socket-based service (server/*.py) derives its port from
# base_port + a fixed offset, rather than each service needing its own config
# field. Offsets matching well-known port numbers (80, 443, 21) make a node's
# ports self-documenting -- base_port=10000 means http is 10080, immediately
# recognizable. file_server has no real-world standard to overlay, so it just
# gets a small offset of its own.
SERVICE_PORT_OFFSETS: dict = {
    "file_server": 1,
    "http": 80,
    "https": 443,
    "ftp": 21,
}


def port_for(config: dict, service_name: str) -> int:
    """The port a given per-drive service should bind to, derived from this
    drive's base_port. Raises KeyError if service_name isn't in
    SERVICE_PORT_OFFSETS (a typo, or a service that hasn't been added there).
    """
    return config["base_port"] + SERVICE_PORT_OFFSETS[service_name]


# Optional keys and their defaults, merged into a valid config after loading.
#   backup: str | None -- the *volume label* of a drive to mirror this drive's
#            <drive>:\I\ folder onto (see service/backup.py). None disables
#            backups for this drive. A label (not a boolean) so different
#            drives can target different backup destinations.
DEFAULT_VALUES: dict = {
    "backup": None,
}


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


def pod_config(path: Path) -> dict | None:
    """The BITU config of the pod `path` lives on, or None if that drive
    isn't opted in. Use this to gate behaviour on BITU drives; pod_root()
    itself deliberately doesn't require a config.
    """
    return load_drive_config(pod_root(path))
