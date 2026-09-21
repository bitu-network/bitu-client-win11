# file: src/pod/_old/peers.py
from pathlib import Path
import re
from pod.paths import get_peers_root

SOCKET_RE = re.compile(r"^([a-zA-Z0-9.-]+|\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$")

def validate_socket(socket: str) -> bool:
    match = SOCKET_RE.fullmatch(socket)
    if not match:
        return False
    port = int(match.group(2))
    return 1 <= port <= 65535

def add_peer(socket: str, alias: str) -> Path:
    """
    Adds a new peer file with:
      - first line = socket
      - second line = public key placeholder
    Returns Path to the created file.
    """
    if not validate_socket(socket):
        raise ValueError("Invalid socket format, use host:port")

    peers_root = get_peers_root()
    if not peers_root:
        raise FileNotFoundError(".pod root not found")

    peers_root.mkdir(exist_ok=True)
    peer_file = peers_root / alias

    if peer_file.exists():
        raise FileExistsError(f"Alias '{alias}' already exists")

    with peer_file.open("w", encoding="utf-8") as f:
        f.write(f"{socket}\n\n")  # public key to be filled later

    return peer_file
