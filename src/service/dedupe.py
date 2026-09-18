# file: src/service/dedupe.py
# description: per-drive content-addressable dedupe service (the "librarian behind
# the scenes"). At startup, runs one full reconciliation scan over <drive>:\-\
# (cheap for already-indexed files -- the hardlink-count check in
# lib/dedupe_core.py skips them before any hashing), covering both the
# never-indexed-before case and catching up on anything missed while this
# service wasn't running (crash, reboot, drive unplugged). Then switches to a
# live watchdog observer for incremental updates: on each new file, hashes
# genuinely new content into the CAS tree at
# <drive>:\o\<byte1>\<byte2>\<hash>\content.<ext>, and flags true duplicates
# (same hash, different inode) for confirmation rather than auto-deleting them.
#
# No periodic re-scan while running -- the live watcher is trusted to catch
# everything in between restarts. Use cli/dedupe.py for an on-demand manual
# reconciliation if you want extra assurance without restarting the service.
#
# Launched once per drive by cli/start.py, only for drives with a valid
# <drive>:\I\-\bitu\config.json (see lib/drives.py).

from __future__ import annotations

import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from lib.cas import cas_root
from lib.dedupe_core import full_scan, process_file
from lib.drives import load_drive_config

SCAN_ROOT_REL = Path("-")  # <drive>:\-\


def _log(msg: str) -> None:
    print(f"[dedupe] {msg}", flush=True)


class _NewFileHandler(FileSystemEventHandler):
    def __init__(self, drive_root: Path):
        self.drive_root = drive_root

    def on_created(self, event):
        if event.is_directory:
            return
        process_file(self.drive_root, Path(event.src_path), log=_log)

    def on_moved(self, event):
        # A move/rename introduces a "new" path that also needs indexing.
        if event.is_directory:
            return
        process_file(self.drive_root, Path(event.dest_path), log=_log)


def main():
    if len(sys.argv) < 2:
        print("[dedupe] Usage: dedupe.py <drive-letter, e.g. D:>", file=sys.stderr)
        sys.exit(1)

    drive_letter = sys.argv[1].rstrip("\\/").upper()
    if not drive_letter.endswith(":"):
        drive_letter += ":"
    drive_root = Path(drive_letter + "\\")

    config = load_drive_config(drive_root)
    if not config:
        print(f"[dedupe] No valid config for {drive_root}; exiting.", flush=True)
        sys.exit(0)

    scan_root = drive_root / SCAN_ROOT_REL
    if not scan_root.is_dir():
        _log(f"scan root {scan_root} does not exist; nothing to do.")
        sys.exit(0)

    cas_root(drive_root).mkdir(parents=True, exist_ok=True)

    _log(f"running startup reconciliation scan of {scan_root} ...")
    count = full_scan(drive_root, scan_root, log=_log)
    _log(f"startup scan complete ({count} files processed).")

    observer = Observer()
    observer.schedule(_NewFileHandler(drive_root), str(scan_root), recursive=True)
    observer.start()
    _log(f"watching {scan_root} for new files...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()