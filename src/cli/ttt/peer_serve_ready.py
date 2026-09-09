# file: src/cli/ttt/peer_serve_ready.py
from threading import Thread
from lib.network import start_listener
from pod.peers import run_command_loop

def peer_ready(biou_root, port):
    Thread(target=start_listener, args=(port, biou_root), daemon=True).start()
    print(f"[ready] Peer listening on port {port}.")
    try:
        run_command_loop()
    except KeyboardInterrupt:
        print("\n[stopped] Peer is no longer available.")




def default_handle_incoming_message(message: str, ip: str):
    """Default handler that dispatches messages to CLI commands."""
    words = message.split()
    if not words:
        return
    clix_root = Path.cwd() / "clix"
    dispatch_cli_command(clix_root, words)
    print(f"[recv] ← {ip}: {message}")
