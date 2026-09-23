# file: src/cli/dev/ttt/on.py
import socket
from pathlib import Path
from pod.peers import dispatch_cli_command

def send_message(ip: str, port: int, message: str):
    """Send a plain-text message to another peer."""
    try:
        with socket.create_connection((ip, port), timeout=3) as s:
            s.sendall(message.encode("utf-8"))
        print(f"[sent] → {ip}:{port}")
    except OSError as e:
        print(f"[error] Could not send message to {ip}:{port}: {e}")


def start_listener(port: int, biou_root: Path):
    """
    Start a simple TCP listener for incoming peer messages and route them to clix.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(5)
    print(f"[peer] Listening on port {port}...")

    while True:
        conn, addr = s.accept()
        ip, _ = addr
        data = conn.recv(4096)
        conn.close()
        if not data:
            continue
        message = data.decode("utf-8", errors="replace")
        handle_incoming_message(message)
        print(f"[recv] ← {ip}: {message.strip()}")


def handle_incoming_message(message: str):
    """
    Handles messages from network and routes them to clix.
    """
    words = message.strip().split()
    if not words:
        return

    clix_root = Path.cwd() / "clix"  # <-- network router root
    dispatch_cli_command(clix_root, words)
