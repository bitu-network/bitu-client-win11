# file: src/cli/clix.py

import sys
from pathlib import Path
from lib.network import send_message
from peer.resolve_alias import resolve_alias_to_ip_port

def main():
    """
    Usage: biou call <peer_alias_or_pubkey> tell <command_words...>
    """
    if len(sys.argv) < 4 or sys.argv[2] != "tell":
        print("Usage: biou call <peer_alias_or_pubkey> tell <command_words...>")
        sys.exit(1)

    peer_id = sys.argv[1]
    command_words = sys.argv[3:]

    # Resolve peer alias/pubkey → (ip, port)
    try:
        ip, port = resolve_alias_to_ip_port(peer_id)
    except ValueError as e:
        print(f"[error] {e}")
        sys.exit(1)

    # Join command words into single string to send
    message = " ".join(command_words)

    # Send message to peer
    send_message(ip, port, message)
