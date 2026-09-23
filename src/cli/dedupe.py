# file: src/cli/dedupe.py

# description: on-demand manual reconciliation scan, for when the archive owner
# wants extra assurance that everything under <pod>\-\ is indexed into the
# CAS tree without restarting the live service/dedupe.py process. Uses the same
# lib/dedupe_core.scan_pod() the service runs at startup, so results are
# identical -- this is just a way to trigger it on demand.
#
# Usage:
#   python -m cli.dedupe D:            # scan one drive
#   python -m cli.dedupe D:\pod_1      # scan one pod nested inside a disk
#   python -m cli.dedupe --all         # scan every pod with a valid BITU config

from __future__ import annotations

import sys

from lib.dedupe_core import scan_pod
from pod.bootstrap import parse_pod_arg
from pod.drives import find_bitu_drives, load_drive_config


def _log(msg: str) -> None:
    print(f"[dedupe-cli] {msg}", flush=True)


def main():
    if len(sys.argv) < 2:
        print("[dedupe-cli] Usage: dedupe.py <pod, e.g. D: or D:\\pod_1> | --all", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--all":
        drives = find_bitu_drives()
        if not drives:
            _log("no pods with a valid BITU config found.")
            return
        for drive_root, _config in drives:
            scan_pod(drive_root, log=_log)
        return

    drive_root = parse_pod_arg(sys.argv[1])
    if not load_drive_config(drive_root):
        print(f"[dedupe-cli] No valid config for {drive_root}; nothing to do.", flush=True)
        sys.exit(1)

    scan_pod(drive_root, log=_log)


if __name__ == "__main__":
    main()
