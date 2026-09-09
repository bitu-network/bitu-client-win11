# file: src/cli/peer/add.py
## biou pod peer add <socket> <alias>

import sys
import re
import sqlite3
from pathlib import Path

# -----------------------
# Constants
# -----------------------
POD_FILE_NAME = ".pod"

# host (domain or IPv4) : port
SOCKET_RE = re.compile(
    r"^([a-zA-Z0-9.-]+|\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$"
)


# -----------------------
# Helpers
# -----------------------



def validate_socket(socket: str) -> tuple[str, int] | None:
    """Validate socket and return (host, port)."""
    m = SOCKET_RE.fullmatch(socket)
    if not m:
        return None
    port = int(m.group(2))
    if not (1 <= port <= 65535):
        return None
    return m.group(1), port


def connect_db(pod_file: Path) -> sqlite3.Connection:
    return sqlite3.connect(pod_file)


# -----------------------
# CLI
# -----------------------
def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: biou pod peer add <socket> <alias>", file=sys.stderr)
        return 1

    socket, alias = argv[1], argv[2]

    parsed = validate_socket(socket)
    if not parsed:
        print("Invalid socket. Use host:port or ip:port.", file=sys.stderr)
        return 1

    pod_file = find_pod_file(Path.cwd())
    if not pod_file:
        print("Error: .pod sqlite file not found.", file=sys.stderr)
        return 1

    host, port = parsed
    socket_norm = f"{host}:{port}"

    try:
        conn = connect_db(pod_file)
        cur = conn.cursor()

        # enforce alias uniqueness
        cur.execute("SELECT 1 FROM peers WHERE alias = ?", (alias,))
        if cur.fetchone():
            print(f"Error: alias '{alias}' already exists.", file=sys.stderr)
            return 1

        # insert peer with unknown public_key for now
        # public_key is temporarily set to alias-prefixed placeholder
        placeholder_pubkey = f"pending:{alias}"

        cur.execute(
            """
            INSERT INTO peers (public_key, socket, alias)
            VALUES (?, ?, ?)
            """,
            (placeholder_pubkey, socket_norm, alias),
        )

        conn.commit()
        conn.close()

    except sqlite3.IntegrityError as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"[added] peer '{alias}' @ {socket_norm} (pending public key)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
