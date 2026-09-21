# file: src/service/dedupe.py
# description: global content-addressable dedupe service (the "librarian behind
# the scenes"). Unlike file_server.py (per-drive, under server/ -- needs real
# process/socket isolation for network simulation), dedupe has no networking
# concern, so one process manages every opted-in drive: periodically rescans
# for drives with a valid <drive>:\I\-\bitu\config.json (see lib/drives.py),
# runs a startup/reconciliation full_scan on any newly seen drive, and
# maintains one watchdog observer schedule per drive for live incremental
# updates -- unscheduling a drive's watch if it's unplugged or its config
# becomes invalid, and picking up newly plugged-in drives on the next check.
#
# Duplicates are replaced with a hardlink to the existing CAS blob
# automatically (lib/dedupe_core.apply_dedupe) -- safe unconditionally, since
# the hash match already confirms the content is byte-for-byte identical.
#
# Auto-discovered and launched once by cli/start.py (any .py file directly
# under service/ is spawned once with no arguments). Use cli/dedupe.py for an
# on-demand manual reconciliation of a specific drive without waiting for
# this service's own periodic checks.

from __future__ import annotations

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from lib.cas import cas_root
from lib.dedupe_core import full_scan, process_file
from pod.drives import find_bitu_drives

SCAN_ROOT_REL = Path("-")  # <drive>:\-\
DRIVE_RESCAN_INTERVAL_SECONDS = 60


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


def _start_watching(observer: Observer, drive_root: Path):
    """Run the startup/reconciliation scan for a newly seen drive and
    register a live watch on it. Returns the watchdog watch handle (for
    later unschedule()), or None if there's nothing to watch.
    """
    scan_root = drive_root / SCAN_ROOT_REL
    if not scan_root.is_dir():
        _log(f"scan root {scan_root} does not exist; not watching {drive_root}.")
        return None

    cas_root(drive_root).mkdir(parents=True, exist_ok=True)

    _log(f"running startup reconciliation scan of {scan_root} ...")
    count = full_scan(drive_root, scan_root, log=_log)
    _log(f"startup scan of {drive_root} complete ({count} files processed).")

    watch = observer.schedule(_NewFileHandler(drive_root), str(scan_root), recursive=True)
    _log(f"watching {scan_root} for new files.")
    return watch


def main():
    observer = Observer()
    observer.start()

    watched: dict[str, object] = {}  # drive letter (e.g. "D:") -> watchdog watch handle

    _log(f"scanning for BITU drives every {DRIVE_RESCAN_INTERVAL_SECONDS}s.")
    try:
        while True:
            current = {root.drive: root for root, _config in find_bitu_drives()}

            # Stop watching drives that disappeared or lost a valid config.
            for letter in list(watched):
                if letter not in current:
                    try:
                        observer.unschedule(watched[letter])
                    except Exception:
                        pass
                    del watched[letter]
                    _log(f"stopped watching {letter} (unplugged or config no longer valid).")

            # Start watching newly seen drives.
            for letter, drive_root in current.items():
                if letter not in watched:
                    watch = _start_watching(observer, drive_root)
                    if watch is not None:
                        watched[letter] = watch

            time.sleep(DRIVE_RESCAN_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
