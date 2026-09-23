# file: src/cli/peer/list.py
## bitu peer list
# Lists the peers configured on the pod the current directory is on.

import sys

from pod.peers import PeerError, list_peers

_HEADERS = ["ALIAS", "SOCKET", "PUBKEY"]


def _print_table(peers: list[dict]) -> None:
    if not peers:
        print("[info] No peers found.")
        return

    rows = [[p["alias"], p["socket"], p["public_key"] or "pending"] for p in peers]
    widths = [max(len(r[i]) for r in rows + [_HEADERS]) for i in range(len(_HEADERS))]

    print(" | ".join(h.ljust(widths[i]) for i, h in enumerate(_HEADERS)))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(" | ".join(row[i].ljust(widths[i]) for i in range(len(_HEADERS))))


def main(argv: list[str] | None = None) -> int:
    try:
        peers = list_peers()
    except PeerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    _print_table(peers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
