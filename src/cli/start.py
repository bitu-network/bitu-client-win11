# file: src/cli/start.py

# description: master startup routine launching background services: the hotkey
# engine, and for every drive with a valid <drive>:\I\-\bitu\config.json (see
# lib/drives.py) a pair of per-drive processes -- service/dedupe.py (the
# filesystem-internal CAS/dedupe librarian) and server/file_server.py (the
# network-facing responder for that drive). A drive with no config, or a config
# missing required fields, simply doesn't get either process -- that's the
# intended way to opt a drive in/out, no separate GUI/TUI toggle needed.

from __future__ import annotations

import os
import subprocess
import sys

from lib.ensures_single_instance import ensure_single_instance
from lib.drives import find_bitu_drives
from project import get_project_root, get_src_root


def main():
    project_root = get_project_root()
    src_dir = get_src_root()

    if not ensure_single_instance("bitu_main_runner"):
        print("[!] Bitu is already running.", flush=True)
        sys.exit(0)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    env["PYTHONUNBUFFERED"] = "1"

    hotkeys_script = src_dir / "service" / "hotkey_engine.py"
    dedupe_script = src_dir / "service" / "dedupe.py"
    file_server_script = src_dir / "server" / "file_server.py"

    print("=== Launching BITU Background Services (Console Output Active) ===", flush=True)
    hotkey_proc = None
    per_drive_procs: list[subprocess.Popen] = []

    try:
        drives = find_bitu_drives()
        if drives:
            print(f"[+] Found {len(drives)} drive(s) with a BITU config:", flush=True)
        for drive_root, config in drives:
            print(f"    {drive_root} -> port {config.get('port')}", flush=True)

            dedupe_proc = subprocess.Popen(
                [sys.executable, str(dedupe_script), drive_root.drive],
                cwd=str(project_root),
                env=env,
                stdout=None,
                stderr=None,
            )
            per_drive_procs.append(dedupe_proc)

            file_server_proc = subprocess.Popen(
                [sys.executable, str(file_server_script), drive_root.drive],
                cwd=str(project_root),
                env=env,
                stdout=None,
                stderr=None,
            )
            per_drive_procs.append(file_server_proc)

        hotkey_proc = subprocess.Popen(
            [sys.executable, str(hotkeys_script)],
            cwd=str(project_root),
            env=env,
            stdout=None,
            stderr=None
        )

        hotkey_proc.wait()
    except KeyboardInterrupt:
        print("\n[!] Terminal closed or interrupted. Shutting down services...", flush=True)
    except Exception as e:
        print(f"[ERROR] Engine orchestration failure: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        for proc in [hotkey_proc, *per_drive_procs]:
            if proc and proc.poll() is None:
                proc.terminate()
        print("[+] All services terminated cleanly.", flush=True)


if __name__ == "__main__":
    main()