# file: src/cli/peer/add.py
## bitu peer add <socket> <alias>
# Adds a peer to the config.json of the pod the current directory is on.

import sys

from pod.peers import PeerError, add_peer


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    if len(argv) != 3:
        print("Usage: bitu peer add <socket> <alias>", file=sys.stderr)
        return 1

    socket, alias = argv[1], argv[2]
    try:
        peer = add_peer(socket, alias)
    except PeerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"[added] peer '{peer['alias']}' @ {peer['socket']} (pending public key)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
