# file: src/hotkeys/o_ctrl.py

import hashlib
import os
from pathlib import Path

from apps.explorer import redirect_active_explorer
from lib.hotkey_context import get_context_fields


def compute_sha256(file_path):
    """Computes the SHA-256 hash of a file to determine its blob address."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def open_sharded_location():
    application, selected_items = get_context_fields(
        "application",
        "selected_items",
    )

    if application != "explorer.exe":
        return

    if not selected_items or len(selected_items) != 1:
        return

    selected = Path(selected_items[0])
    if not selected.exists() or not selected.is_file():
        return

    # Ignore .lnk shortcuts (letting standard OS tools or right-click handle them)
    if selected.suffix.lower() == ".lnk":
        return

    # Compute SHA-256 hash for 2-byte sharding + full hash folder (o/byte1/byte2/hash/)
    file_hash = compute_sha256(selected)
    byte1 = file_hash[0:2]
    byte2 = file_hash[2:4]

    drive_root = Path(selected.anchor)
    sharded_dir = drive_root / "o" / byte1 / byte2 / file_hash

    # If the sharded directory doesn't exist, instantiate it and seed with a hard link
    if not sharded_dir.exists():
        sharded_dir.mkdir(parents=True, exist_ok=True)
        sharded_link_path = sharded_dir / selected.name
        try:
            os.link(selected, sharded_link_path)
        except OSError:
            pass  # Failsafe for cross-device links or access limitations

    # Open/redirect active Explorer window straight to the exclusive hash directory
    redirect_active_explorer(sharded_dir)


open_sharded_location()