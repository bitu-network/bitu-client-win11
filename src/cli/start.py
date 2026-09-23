# file: src/cli/start.py
# description: master startup routine. Auto-discovers and launches every
# service under src/service/ (global services, spawned once with no
# arguments -- e.g. hotkey_engine.py, backup.py, dedupe.py: none of these
# need per-drive process isolation) and src/server/ (per-drive services,
# spawned once per pod found by pod/drives.find_bitu_drives() -- a drive or a
# volume nested inside one, e.g. D:\pod_1 -- with that pod's root path as the
# sole argument, e.g. external_http_server.py, which
# needs real process/socket isolation per drive for the mesh-network
# simulation and sensitive-data isolation goals). Adding a new service means
# dropping a .py file in the right folder; this file never needs to change
# for that.
#
# A file is skipped if its name starts with "_" (helper modules, not meant to
# be run directly) or if it's not directly a .py file. Renaming a service's
# extension from .py to .py.off is the mechanism for disabling it, and needs
# no exclusion logic of its own: glob("*.py") simply never matches a
# ".py.off" file in the first place.
#
# A drive with no valid <drive>:\I\-\bitu\config.json (see lib/drives.py)
# gets none of the per-drive (server/) services -- that's the intended way to
# opt a drive in/out, no separate GUI/TUI toggle needed.

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from lib.ensures_single_instance import ensure_single_instance
from pod.drives import find_bitu_drives
from project import get_project_root, get_src_root


def _discover_services(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.glob("*.py")
        if p.is_file() and not p.name.startswith("_")
    )


def main():
    project_root = get_project_root()
    src_dir = get_src_root()

    if not ensure_single_instance("bitu_main_runner"):
        print("[!] Bitu is already running.", flush=True)
        sys.exit(0)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    env["PYTHONUNBUFFERED"] = "1"

    global_scripts = _discover_services(src_dir / "service")
    drive_scripts = _discover_services(src_dir / "server")

    print("=== Launching BITU Background Services (Console Output Active) ===", flush=True)
    procs: list[subprocess.Popen] = []

    try:
        for script in global_scripts:
            print(f"[+] Starting global service: {script.name}", flush=True)
            proc = subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(project_root),
                env=env,
                stdout=None,
                stderr=None,
            )
            procs.append(proc)

        drives = find_bitu_drives()
        if drives:
            print(f"[+] Found {len(drives)} drive(s) with a BITU config:", flush=True)
        for drive_root, config in drives:
            print(f"    {drive_root} -> port {config.get('port')}", flush=True)
            for script in drive_scripts:
                print(f"    [+] Starting {script.name} for {drive_root}", flush=True)
                proc = subprocess.Popen(
                    [sys.executable, str(script), str(drive_root)],
                    cwd=str(project_root),
                    env=env,
                    stdout=None,
                    stderr=None,
                )
                procs.append(proc)

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Terminal closed or interrupted. Shutting down services...", flush=True)
    except Exception as e:
        print(f"[ERROR] Engine orchestration failure: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        for proc in procs:
            if proc and proc.poll() is None:
                proc.terminate()
        print("[+] All services terminated cleanly.", flush=True)


if __name__ == "__main__":
    main()
