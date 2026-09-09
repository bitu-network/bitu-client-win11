# file: src/cli/port/set.py

import sys
from pathlib import Path

from pod.paths import get_config_root


def validate_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise ValueError("port must be an integer")

    if not (1 <= port <= 65535):
        raise ValueError("port must be in range 1–65535")

    return port


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: biou pod port set <port>", file=sys.stderr)
        return 1

    try:
        port = validate_port(argv[1])
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    cwd = Path.cwd()
    config_root = get_config_root(cwd)
    if not config_root:
        print("error: not inside a .pod root", file=sys.stderr)
        return 1

    config_root.mkdir(parents=True, exist_ok=True)

    port_file = config_root / "port"
    port_file.write_text(f"{port}\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
