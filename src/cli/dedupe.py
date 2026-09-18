# file: src/cli/dedupe.py

# description: on-demand manual reconciliation scan, for when the archive owner
# wants extra assurance that everything under <drive>:\-\ is indexed into the
# CAS tree without restarting the live service/dedupe.py process. Uses the same
# lib/dedupe_core.full_scan() the service runs at startup, so results are
# identical -- this is just a way to trigger it on demand.
#
# Usage:
#   python -m cli.dedupe D:            # scan one drive
#   python -m cli.dedupe --all         # scan every drive with a valid BITU config

from __future__ import annotations

import sys
from pathlib import Path

from lib.dedupe_core import full_scan
from lib.drives import find_bitu_drives, load_drive_config


def _log(msg: str) -> None:
    print(f"[dedupe-cli] {msg}", flush=True)


def _scan_drive(drive_root: Path) -> None:
    scan_root = drive_root / "-"
    if not scan_root.is_dir():
        _log(f"{drive_root}: scan root {scan_root} does not exist; skipping.")
        return
    _log(f"{drive_root}: scanning {scan_root} ...")
    count = full_scan(drive_root, scan_root, log=_log)
    _log(f"{drive_root}: done ({count} files processed).")


def main():
    if len(sys.argv) < 2:
        print("[dedupe-cli] Usage: dedupe.py <drive-letter, e.g. D:> | --all", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--all":
        drives = find_bitu_drives()
        if not drives:
            _log("no drives with a valid BITU config found.")
            return
        for drive_root, _config in drives:
            _scan_drive(drive_root)
        return

    drive_letter = sys.argv[1].rstrip("\\/").upper()
    if not drive_letter.endswith(":"):
        drive_letter += ":"
    drive_root = Path(drive_letter + "\\")

    config = load_drive_config(drive_root)
    if not config:
        print(f"[dedupe-cli] No valid config for {drive_root}; nothing to do.", flush=True)
        sys.exit(1)

    _scan_drive(drive_root)


if __name__ == "__main__":
    main()