# file: src/cli/init/init_config.py
# description: interactive wizard for src/cli/init.py. Writes
# <drive>:\I\-\bitu\config.json for the drive detected by init.py (or the
# current working directory's drive, if run standalone), suggesting a
# well-spaced default base_port by scanning other mounted drives' existing
# configs. Every per-drive socket-based service (server/*.py) derives its own
# port from base_port + a fixed offset (see lib/config.SERVICE_PORT_OFFSETS) --
# e.g. base_port=10000 means file_server is 10001, http is 10080, https is
# 10443 -- so suggestions are spaced 1000 apart (comfortably wider than the
# largest offset, 443) to guarantee two nodes' derived port ranges never
# overlap even without checking every individual offset.
#
# Run via init.py, but works standalone too (falls back to detecting its own
# drive root from cwd) for testing this one wizard step in isolation.

from __future__ import annotations

import json
from pathlib import Path

from pod.config import config_path, load_drive_config
from pod.drives import enumerate_drive_roots

BASE_PORT_START = 10000
BASE_PORT_STEP = 1000
MAX_PORT_SCAN = 1000  # give up after this many candidates rather than looping forever


def _drive_root() -> Path:
    injected = globals().get("DRIVE_ROOT")
    if injected is not None:
        return injected
    return Path(Path.cwd().anchor)


def _used_base_ports() -> set[int]:
    used = set()
    for root in enumerate_drive_roots():
        config = load_drive_config(root)
        if config and "base_port" in config:
            used.add(config["base_port"])
    return used


def _suggest_base_port() -> int:
    used = _used_base_ports()
    for offset in range(MAX_PORT_SCAN):
        candidate = BASE_PORT_START + offset * BASE_PORT_STEP
        if candidate not in used:
            return candidate
    return BASE_PORT_START  # fallback if somehow every candidate in range is taken


def _prompt_base_port(default_base_port: int) -> int:
    while True:
        raw = input(f"Base port for this drive's BITU node [{default_base_port}]: ").strip()
        if not raw:
            return default_base_port
        try:
            base_port = int(raw)
        except ValueError:
            print("[!] Please enter a number.")
            continue
        if not (1 <= base_port <= 65535 - 443):
            print("[!] Base port must leave room for the highest offset (https, +443).")
            continue
        return base_port


def main():
    drive_root = _drive_root()
    path = config_path(drive_root)

    existing = load_drive_config(drive_root)
    if existing is not None:
        while True:
            choice = input(
                f"[!] A valid config already exists at {path} "
                f"(base_port {existing.get('base_port')}).\n"
                "Do you want to (A)bort or (O)verwrite? [A/O]: "
            ).strip().upper()
            if choice == "A":
                print("[i] Keeping existing config.")
                return
            elif choice == "O":
                break
            else:
                print("[!] Invalid choice. Please enter 'A' or 'O'.")

    default_base_port = _suggest_base_port()
    base_port = _prompt_base_port(default_base_port)

    config = {"base_port": base_port}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"[\u2713] Wrote {path}")


if __name__ == "__main__":
    main()
