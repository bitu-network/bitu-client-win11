# file: src/cli/peer/alias.py
## bitu peer alias <alias|pubkey> <new_alias>
# Renames a peer in the config.json of the pod the current directory is on.

import sys

from pod.peers import PeerError, set_peer_alias


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    if len(argv) != 3:
        print("Usage: bitu peer alias <alias|pubkey> <new_alias>", file=sys.stderr)
        return 1

    ref, new_alias = argv[1], argv[2]
    try:
        peer = set_peer_alias(ref, new_alias)
    except PeerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"[updated] peer '{ref}' -> '{peer['alias']}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
