# file: src/lib/network.py
import socket
from pathlib import Path
# from peering import dispatch_cli_command


def send_message(ip: str, port: int, message: str):
    """Send a plain-text message to another peer."""
    try:
        with socket.create_connection((ip, port), timeout=3) as s:
            s.sendall(message.encode("utf-8"))
        print(f"[sent] → {ip}:{port}")
    except OSError as e:
        print(f"[error] Could not send message to {ip}:{port}: {e}")


def start_listener(port: int, on_message=None):
    """
    Start a simple TCP listener for incoming peer messages.

    Args:
        port: TCP port to listen on.
        on_message: Optional callback(message:str, ip:str)
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
        message = data.decode("utf-8", errors="replace").strip()
        if on_message:
            on_message(message, ip)


