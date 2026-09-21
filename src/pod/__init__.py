# file: src/pod/__init__.py
# description: a pod is a drive. Paths on it, its opt-in config, and which
# drives exist all live in this package.

from .paths import (
    BLOBS_DIR,
    CONCEPTS_DIR,
    PERSONAL_CALENDAR_DIR,
    PERSONAL_CONCEPTS_DIR,
    blobs_root,
    concepts_root,
    interpret_path,
    personal_calendar_root,
    personal_concepts_root,
    pod_root,
    relative_path,
)
from .config import (
    CONFIG_REL_PATH,
    config_path,
    load_drive_config,
    pod_config,
    port_for,
)
from .drives import (
    enumerate_drive_roots,
    find_bitu_drives,
    find_drive_by_label,
    get_volume_label,
)

__all__ = [
    "BLOBS_DIR",
    "CONCEPTS_DIR",
    "CONFIG_REL_PATH",
    "PERSONAL_CALENDAR_DIR",
    "PERSONAL_CONCEPTS_DIR",
    "blobs_root",
    "concepts_root",
    "config_path",
    "enumerate_drive_roots",
    "find_bitu_drives",
    "find_drive_by_label",
    "get_volume_label",
    "interpret_path",
    "load_drive_config",
    "personal_calendar_root",
    "personal_concepts_root",
    "pod_config",
    "pod_root",
    "port_for",
    "relative_path",
]
