# file: src/server/external_http_server.py


from __future__ import annotations

import sys
from pathlib import Path

from pod.config import port_for
from pod.drives import load_drive_config
from lib.http_app import create_app
from project import get_src_root

WEB_PUBLIC_ROOT = get_src_root() / "http" / "external"


def main():
    if len(sys.argv) < 2:
        print("[http_server] Usage: http_server.py <drive-letter, e.g. D:>", file=sys.stderr)
        sys.exit(1)

    drive_letter = sys.argv[1].rstrip("\\/").upper()
    if not drive_letter.endswith(":"):
        drive_letter += ":"
    drive_root = Path(drive_letter + "\\")

    config = load_drive_config(drive_root)
    if not config:
        print(f"[http_server] No valid config for {drive_root}; exiting.", flush=True)
        sys.exit(0)

    port = port_for(config, "http")
    print(f"[http_server] {drive_root} -> 127.0.0.1:{port} serving {WEB_PUBLIC_ROOT}", flush=True)

    app = create_app(WEB_PUBLIC_ROOT)
    app.run(host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
