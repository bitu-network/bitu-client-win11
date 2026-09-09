# file: src/cli/dev/watch/rust.py

import subprocess
import sys
from pathlib import Path
from project import get_project_root


def main():
    rust_core_dir = get_project_root() / "src_rust_core"
    if not rust_core_dir.exists():
        rust_core_dir = Path("src_rust_core")

    try:
        subprocess.run(
            ["cargo", "watch", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        print("[*] 'cargo-watch' not found. Installing automatically...")
        subprocess.run(["cargo", "install", "cargo-watch"], check=True)

    print("[*] Starting cargo-watch for maturin develop in rust_core...")
    try:
        subprocess.run(
            ["cargo", "watch", "-s", "maturin develop"], cwd=rust_core_dir, check=True
        )
    except KeyboardInterrupt:
        print("\n[!] Stopped maturin watch.")


if __name__ == "__main__":
    main()
