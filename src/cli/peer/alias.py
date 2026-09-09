# file: src/cli/peer/alias.py
import sys
from pod.peers import set_peer_alias

def main():
    if len(sys.argv) != 3:
        print("Usage: biou peer alias <pubkey|alias|truncated_pubkey> <new_alias>")
        sys.exit(1)

    peer_dir = set_peer_alias(sys.argv[1], sys.argv[2])
    if not peer_dir:
        print("[error] Could not set alias.")
        sys.exit(1)

    print(f"[updated] Alias for {peer_dir.name[:12]}... set to '{sys.argv[2]}'")

if __name__ == "__main__":
    main()
