# file: src/pod/peers.[old].py
"""
Peer management and messaging utilities for the BIOU network.

Modules included:
- resolve.py: Locate peer directories by pubkey, truncated pubkey, or alias.
- peer_settings.py: Add, update, and list peers.
- message_store.py: Persist messages with timestamped filenames.
- dispatcher.py: CLI command dispatching and network messaging loop.

This file provides a consolidated, well-documented interface for working with peers.
"""

import re
import sys
import time
from pathlib import Path
from datetime import datetime
import importlib.util
from typing import Optional, List


from lib.low_level_helpers import write_file, read_file, format_timestamp
from lib.fs.fs_utils import safe_folder_name
from lib.formatters import truncate
from lib.models import PeerInfo
from lib.network import send_message
from fs.locating import get_peers_root

# -----------------------
# Constants / Defaults
# -----------------------

DEFAULT_TLS = None
DEFAULT_ALIAS = None
PUBKEY_RE = re.compile(r"^[0-9a-f]{64}$")

# =======================
# Peer Resolution
# =======================
def resolve_peer(identifier: str, peers_root: Path) -> Optional[Path]:
    """
    Return the path to a peer folder given:
      1. Full pubkey (64 hex chars)
      2. Truncated pubkey prefix
      3. Alias

    Args:
        identifier: The pubkey, truncated pubkey, or alias.
        peers_root: Root folder containing all peer directories.

    Returns:
        Path to the peer directory if found, else None.
    """
    # Full pubkey match
    if PUBKEY_RE.match(identifier):
        candidate = peers_root / identifier
        if candidate.exists():
            return candidate

    # Truncated pubkey match
    for pubkey_dir in peers_root.iterdir():
        if pubkey_dir.is_dir() and pubkey_dir.name.startswith(identifier):
            return pubkey_dir

    # Alias match
    for pubkey_dir in peers_root.iterdir():
        alias_file = pubkey_dir / "alias"
        if alias_file.exists():
            alias = alias_file.read_text().strip()
            if alias == identifier:
                return pubkey_dir

    return None

# =======================
# Peer Management
# =======================


def add_peer(pubkey: str, socket: str, tls: Optional[bool] = None,
             alias: Optional[str] = None, root: Optional[Path] = None) -> Optional[PeerInfo]:
    """
    Add or update a peer entry.

    Args:
        pubkey: Peer public key (hex string)
        socket: IP:port or identifier for connection
        tls: Optional TLS flag
        alias: Optional human-readable alias
        root: Optional root path for the archive

    Returns:
        PeerInfo object if successful, else None.
    """
    peers_root = get_peers_root(root)
    if not peers_root:
        return None

    peer_dir = peers_root / pubkey / safe_folder_name(socket)

    write_file(peer_dir / "socket", socket)
    write_file(peer_dir / "last_seen", int(time.time()))
    write_file(peer_dir / "tls", str(tls if tls is not None else DEFAULT_TLS).lower())

    if alias or DEFAULT_ALIAS:
        write_file(peers_root / pubkey / "alias", alias if alias else DEFAULT_ALIAS)

    return PeerInfo(
        pubkey=pubkey,
        socket=socket,
        alias=alias if alias else DEFAULT_ALIAS,
        peer_dir=peer_dir,
        root=peers_root.parent,
    )

def set_peer_alias(identifier: str, new_alias: str, root: Optional[Path] = None) -> Optional[Path]:
    """
    Set or update the alias of a peer by pubkey, truncated pubkey, or alias.

    Args:
        identifier: Peer identifier (pubkey, truncated pubkey, alias)
        new_alias: New alias to assign
        root: Optional root path for the archive

    Returns:
        Path to the peer directory if successful, else None.
    """
    peers_root = get_peers_root(root)
    if not peers_root or not peers_root.exists():
        return None

    peer_dir = resolve_peer(identifier, peers_root)
    if not peer_dir:
        return None

    peer_dir.mkdir(parents=True, exist_ok=True)
    write_file(peer_dir / "alias", new_alias)
    return peer_dir

def get_peer_list(root: Optional[Path] = None) -> List[List[str]]:
    """
    Retrieve a structured list of peers for CLI display.

    Returns:
        List of rows: [alias, short_pubkey, socket, tls, last_seen_str]
    """
    peers_root = get_peers_root(root)
    if not peers_root or not peers_root.exists():
        return []

    rows = []
    for pubkey_dir in sorted(peers_root.iterdir()):
        if not pubkey_dir.is_dir():
            continue

        pubkey = pubkey_dir.name
        alias = read_file(pubkey_dir / "alias", "")

        socket_dirs = [d for d in pubkey_dir.iterdir() if d.is_dir()]
        if not socket_dirs:
            rows.append([alias, truncate(pubkey), "", "", ""])
            continue

        for sdir in socket_dirs:
            socket = read_file(sdir / "socket", sdir.name)
            tls = read_file(sdir / "tls", "")
            last_seen = format_timestamp(read_file(sdir / "last_seen", ""))
            rows.append([alias, truncate(pubkey), socket, tls, last_seen])

    return rows

# =======================
# Message Storage
# =======================
def store_message(biou_root: Path, ip: str, port: int, message: str):
    """
    Store a received message in a timestamped text file.

    Args:
        biou_root: Archive root path
        ip: Peer IP
        port: Peer port
        message: Message content
    """
    peer_dir = biou_root / "peers" / ip / str(port)
    peer_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y.%m.%d %H%M%S")
    file_path = peer_dir / f"{timestamp}.txt"

    file_path.write_text(message)

# =======================
# CLI Dispatching
# =======================
def dispatch_cli_command(base_cli_path: Path, command_words: list[str]):
    """
    Dispatch a command to the corresponding CLI script.

    Args:
        base_cli_path: Base path to CLI scripts
        command_words: Command path as a list of words, e.g. ['foo','bar']
    """
    current_path = base_cli_path
    for word in command_words[:-1]:
        current_path = current_path / word

    script_file = current_path / f"{command_words[-1]}.py"
    if not script_file.exists():
        print(f"[error] Command script not found: {script_file}")
        return

    spec = importlib.util.spec_from_file_location("cli_module", script_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules["cli_module"] = module
    spec.loader.exec_module(module)

    if hasattr(module, "main"):
        module.main()
    else:
        print(f"[error] No main() in {script_file}")

def run_command_loop():
    """
    Simple CLI loop to send messages or exit.
    Commands:
        send <ip> <port> <message>
        quit / exit
    """
    while True:
        line = input("> ").strip()
        if not line:
            continue
        if line in {"quit", "exit"}:
            break
        cmd, *args = line.split()
        if cmd == "send":
            handle_send(args)
        else:
            print("[info] Unknown command. Use `send <ip> <port> <message>` or `quit`.")

def handle_send(args):
    """
    Handle 'send' command from CLI.

    Args:
        args: [ip, port, message parts...]
    """
    if len(args) < 3:
        print("[error] Usage: send <ip> <port> <message>")
        return
    ip, port, *msg = args
    try:
        send_message(ip, int(port), " ".join(msg))
    except Exception as e:
        print(f"[error] {e}")


# def get_peers(conn: sqlite3.Connection):
#     """
#     Return all peers as a list of dicts from the 'peers' table.
#     """
#     cursor = conn.cursor()
#     cursor.execute("SELECT public_key, socket, alias, biou, last_seen FROM peers")
#     cols = [desc[0] for desc in cursor.description]
#     return [dict(zip(cols, row)) for row in cursor.fetchall()]