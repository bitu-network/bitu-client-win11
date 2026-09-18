# file: src/lib/dedupe_core.py

# description: shared "walk a drive and feed files into the CAS tree" logic, used
# by both service/dedupe.py (startup reconciliation + live watchdog handler) and
# cli/dedupe.py (on-demand manual reconciliation). Keeping this here means both
# callers process a file exactly the same way -- there's only one definition of
# what "new content" vs "duplicate" means.

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable

from lib.cas import cas_root, find_existing_blob, hash_file, store_new_blob

PENDING_DEDUPE_LOG_REL = Path("I") / "-" / "bitu" / "pending_dedupe.log"

LogFn = Callable[[str], None]


def _default_log(msg: str) -> None:
    print(f"[dedupe] {msg}", flush=True)


def flag_duplicate(drive_root: Path, path: Path, existing_blob: Path, digest: str,
                    log: LogFn = _default_log) -> None:
    """Record a true duplicate (same hash, different inode) for confirmation.

    Not auto-replaced with a hardlink -- that's destructive, and there's no
    confirmation UI yet. A future confirmation flow should consume this log
    and, on approval, delete `path` and os.link() `existing_blob` in its place.
    """
    log_path = drive_root / PENDING_DEDUPE_LOG_REL
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{time.time()}\t{digest}\t{path}\t{existing_blob}\n")
    log(f"duplicate flagged (pending confirmation): {path} == {existing_blob}")


def process_file(drive_root: Path, path: Path, log: LogFn = _default_log) -> None:
    """Index a single file: skip if it's already a known hardlink, otherwise
    hash it and either store it as a new blob or flag it as a duplicate.
    """
    try:
        st = path.stat()
    except OSError:
        return  # file may have already been moved/deleted

    if st.st_nlink > 1:
        # Already a hardlink to something known (our own store_new_blob() call,
        # or one the user made on purpose) -- nothing new to index.
        return

    digest = hash_file(path)
    if digest is None:
        return

    existing_blob = find_existing_blob(drive_root, digest)
    if existing_blob is None:
        try:
            store_new_blob(drive_root, digest, path)
            log(f"stored new blob {digest} <- {path}")
            return
        except FileExistsError:
            # Race: another process stored this exact hash between our check
            # and now. Fall through and treat it as a duplicate below.
            existing_blob = find_existing_blob(drive_root, digest)

    if existing_blob is not None:
        flag_duplicate(drive_root, path, existing_blob, digest, log=log)


def full_scan(drive_root: Path, scan_root: Path, log: LogFn = _default_log) -> int:
    """Walk scan_root and process_file() every file found. Cheap for files
    already indexed (nlink check short-circuits before any hashing).
    Returns the number of files processed.
    """
    cas_dir = cas_root(drive_root)
    count = 0
    for root, _dirs, files in os.walk(scan_root):
        root_path = Path(root)
        # Don't index our own CAS tree if it's nested under the scan root.
        if root_path == cas_dir or cas_dir in root_path.parents:
            continue
        for name in files:
            process_file(drive_root, root_path / name, log=log)
            count += 1
    return count