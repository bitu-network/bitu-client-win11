# file: src/cli/init/config.py
# description: interactive wizard for src/cli/init.py. Writes
# <drive>:\I\-\bitu\config.json for the drive detected by init.py (or the
# current working directory's drive, if run standalone), suggesting a default
# port by scanning other mounted drives' existing configs for already-used
# ports so two nodes don't accidentally collide.
#
# Run via init.py, but works standalone too (falls back to detecting its own
# drive root from cwd) for testing this one wizard step in isolation.

from __future__ import annotations

import json
from pathlib import Path

from lib.config import config_path, load_drive_config
from lib.drives import enumerate_drive_roots

BASE_PORT = 42000
MAX_PORT_SCAN = 1000  # give up after this many candidates rather than looping forever


def _drive_root() -> Path:
    injected = globals().get("DRIVE_ROOT")
    if injected is not None:
        return injected
    return Path(Path.cwd().anchor)


def _used_ports() -> set[int]:
    used = set()
    for root in enumerate_drive_roots():
        config = load_drive_config(root)
        if config and "port" in config:
            used.add(config["port"])
    return used


def _suggest_port() -> int:
    used = _used_ports()
    for offset in range(MAX_PORT_SCAN):
        candidate = BASE_PORT + offset
        if candidate not in used:
            return candidate
    return BASE_PORT  # fallback if somehow every candidate in range is taken


def _prompt_port(default_port: int) -> int:
    while True:
        raw = input(f"Port for this drive's BITU node [{default_port}]: ").strip()
        if not raw:
            return default_port
        try:
            port = int(raw)
        except ValueError:
            print("[!] Please enter a number.")
            continue
        if not (1 <= port <= 65535):
            print("[!] Port must be between 1 and 65535.")
            continue
        return port


def main():
    drive_root = _drive_root()
    path = config_path(drive_root)

    existing = load_drive_config(drive_root)
    if existing is not None:
        while True:
            choice = input(
                f"[!] A valid config already exists at {path} (port {existing.get('port')}).\n"
                "Do you want to (A)bort or (O)verwrite? [A/O]: "
            ).strip().upper()
            if choice == "A":
                print("[i] Keeping existing config.")
                return
            elif choice == "O":
                break
            else:
                print("[!] Invalid choice. Please enter 'A' or 'O'.")

    default_port = _suggest_port()
    port = _prompt_port(default_port)

    config = {"port": port}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"[\u2713] Wrote {path}")


if __name__ == "__main__":
    main()
