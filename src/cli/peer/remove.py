# file: src/cli/peer/remove.py
## bitu peer remove <alias|pubkey>
# Removes a peer from the config.json of the pod the current directory is on.

import sys

from pod.peers import PeerError, remove_peer


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    if len(argv) != 2:
        print("Usage: bitu peer remove <alias|pubkey>", file=sys.stderr)
        return 1

    ref = argv[1]
    try:
        remove_peer(ref)
    except PeerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"[removed] peer '{ref}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
