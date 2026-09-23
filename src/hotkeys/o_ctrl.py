# file: src/hotkeys/o_ctrl.py

import os
from pathlib import Path

from apps.explorer import redirect_active_explorer
from lib.cas import blob_dir_for_hash, hash_file
from lib.hotkey_context import get_context_fields
from pod.paths import pod_root

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

    # Content address within the file's own pod: <pod>\o\<byte1>\<byte2>\<hash>\
    file_hash = hash_file(selected)
    if file_hash is None:
        return  # unreadable file
    sharded_dir = blob_dir_for_hash(pod_root(selected), file_hash)

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