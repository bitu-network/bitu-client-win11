# file: src/pod/__init__.py
# description: a pod is a mounted volume -- a drive, or a volume nested in a
# folder of another (e.g. D:\pod_1). Paths on it, its opt-in config, its
# peers, and which volumes exist all live in this package.

from .paths import (
    BITU_DIR,
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
    same_pod,
)
from .config import (
    CONFIG_REL_PATH,
    config_path,
    load_drive_config,
    pod_config,
    save_drive_config,
)
from .peers import (
    add_peer,
    list_peers,
    remove_peer,
    set_peer_alias,
    validate_socket,
)
from .keys import (
    generate_keys,
    has_keys,
    key_dir,
    load_private_key,
    load_public_key,
    private_key_path,
    public_key_path,
)
from .drives import (
    enumerate_drive_roots,
    find_bitu_drives,
    find_drive_by_label,
    get_volume_label,
)
from .bootstrap import load_pod_or_exit, parse_pod_arg

__all__ = [
    "BITU_DIR",
    "BLOBS_DIR",
    "CONCEPTS_DIR",
    "CONFIG_REL_PATH",
    "PERSONAL_CALENDAR_DIR",
    "PERSONAL_CONCEPTS_DIR",
    "add_peer",
    "blobs_root",
    "concepts_root",
    "config_path",
    "enumerate_drive_roots",
    "find_bitu_drives",
    "find_drive_by_label",
    "generate_keys",
    "get_volume_label",
    "has_keys",
    "interpret_path",
    "key_dir",
    "list_peers",
    "load_private_key",
    "load_public_key",
    "load_drive_config",
    "load_pod_or_exit",
    "parse_pod_arg",
    "personal_calendar_root",
    "personal_concepts_root",
    "pod_config",
    "pod_root",
    "private_key_path",
    "public_key_path",
    "relative_path",
    "remove_peer",
    "same_pod",
    "save_drive_config",
    "set_peer_alias",
    "validate_socket",
]
