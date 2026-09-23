# file: src/cli/router.py
# description: prototype machine-level router. Owns ONE UDP broadcast socket
# for the whole machine (per the per-machine-service decision -- several
# per-pod routers would just fight over the same adapter) and every mounted
# pod's identity on it, so any pod on this machine can reach any peer by
# public key alone.
#
# A peer is found by broadcasting a signed challenge and verifying whoever
# replies actually holds the matching private key (nacl.signing) -- MAC and
# IP are never trusted as identity, only as a transient "reachable-at" learned
# from a verified reply. The routing table and outbound queues are in-memory
# only, rebuilt from blank on every start: cheap to relearn, not worth
# persisting yet.
#
# This proves the LAN/broadcast protocol first; WLAN hopping across several
# known-but-unassociated networks is future work. Two pods mounted on THIS
# machine can already talk through it as a test of the same code path (their
# packets round-trip through the real socket stack, loopback included).
#
# Kept in cli/ for now so it can be started/stopped standalone in its own
# terminal while prototyping, without cli.start.py having to restart every
# other service -- move to src/service/ once its behavior is trusted.

from __future__ import annotations

import json
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from pod.drives import find_bitu_drives
from pod.keys import has_keys, load_private_key, load_public_key

DISCOVER_PORT = 47623
CHALLENGE_INTERVAL = 10.0    # seconds between wildcard rediscovery sweeps
PEER_STALE_AFTER = 30.0      # forget a peer's address if not reheard this long
RECV_BUFSIZE = 4096
PUBKEY_HEX_LEN = 64          # Ed25519 verify keys are 32 bytes


@dataclass
class Identity:
    root: Path
    public_key_hex: str

    def sign(self, data: bytes) -> bytes:
        return load_private_key(self.root).sign(data).signature


@dataclass
class Peer:
    address: tuple[str, int]
    last_seen: float = field(default_factory=time.time)


class Router:
    """The machine's single broadcaster/listener. Other code (a per-pod
    service, the CLI below) calls send()/drains inbox on this one instance
    rather than opening its own socket.
    """

    def __init__(self, port: int = DISCOVER_PORT):
        self.port = port
        self.identities: dict[str, Identity] = {}              # pubkey hex -> Identity (local pods)
        self.peers: dict[str, Peer] = {}                        # pubkey hex -> Peer (verified, remote or local)
        self.outbox: dict[str, list[tuple[str, bytes]]] = {}    # to_pubkey -> [(from_pubkey, payload)]
        self.inbox: list[tuple[str, bytes]] = []                # (from_pubkey, payload) for callers to drain
        self._lock = threading.Lock()
        self._stop = threading.Event()

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind(("", self.port))

    # -- setup ---------------------------------------------------------------

    def refresh_identities(self) -> None:
        """Re-scan mounted pods for ones with a generated keypair. Safe to
        call anytime -- pods can be plugged/unplugged while the router runs.
        """
        found = {}
        for root, _config in find_bitu_drives():
            if has_keys(root):
                pubkey = load_public_key(root)
                if pubkey:
                    found[pubkey] = Identity(root=root, public_key_hex=pubkey)
        with self._lock:
            self.identities = found

    # -- wire format -----------------------------------------------------------

    def _send_json(self, obj: dict, addr: tuple[str, int]) -> None:
        self._sock.sendto(json.dumps(obj).encode("utf-8"), addr)

    def _broadcast_json(self, obj: dict) -> None:
        self._send_json(obj, ("<broadcast>", self.port))

    # -- outgoing --------------------------------------------------------------

    def challenge(self, target_pubkey: str = "*") -> None:
        """Ask the network 'who's out there' (or 'is pubkey X out there'),
        expecting signed replies only from whoever actually holds that key.
        """
        nonce = secrets.token_hex(16)
        self._broadcast_json({"type": "challenge", "nonce": nonce, "target": target_pubkey})

    def send(self, from_pubkey: str, to_pubkey: str, payload: bytes) -> None:
        """Send `payload` from one of this machine's own pods to a peer,
        identified by public key alone. Delivered immediately if the peer's
        address is already known and fresh; otherwise queued (store-and-
        forward) and a challenge is broadcast to try to (re)discover them.
        """
        with self._lock:
            if from_pubkey not in self.identities:
                raise ValueError(f"'{from_pubkey}' is not a local pod identity")
            peer = self.peers.get(to_pubkey)
            fresh = peer is not None and (time.time() - peer.last_seen) < PEER_STALE_AFTER

        if fresh:
            self._deliver(from_pubkey, to_pubkey, payload, peer.address)
        else:
            with self._lock:
                self.outbox.setdefault(to_pubkey, []).append((from_pubkey, payload))
            self.challenge(to_pubkey)

    def _deliver(self, from_pubkey: str, to_pubkey: str, payload: bytes, addr: tuple[str, int]) -> None:
        with self._lock:
            sender = self.identities.get(from_pubkey)
        if sender is None:
            return  # identity unplugged between queueing and delivery
        signature = sender.sign(payload).hex()
        self._send_json(
            {
                "type": "deliver",
                "to": to_pubkey,
                "from": from_pubkey,
                "payload": payload.hex(),
                "signature": signature,
            },
            addr,
        )

    def _drain_outbox(self, to_pubkey: str) -> None:
        with self._lock:
            peer = self.peers.get(to_pubkey)
            queued = self.outbox.pop(to_pubkey, []) if peer else []
        for from_pubkey, payload in queued:
            self._deliver(from_pubkey, to_pubkey, payload, peer.address)

    # -- incoming --------------------------------------------------------------

    def _handle_challenge(self, msg: dict, addr: tuple[str, int]) -> None:
        target = msg.get("target", "*")
        nonce = msg.get("nonce", "")
        if not nonce:
            return
        with self._lock:
            matches = [idn for pk, idn in self.identities.items() if target in ("*", pk)]
        for idn in matches:
            signature = idn.sign(nonce.encode("utf-8")).hex()
            self._send_json(
                {"type": "response", "pubkey": idn.public_key_hex, "nonce": nonce, "signature": signature},
                addr,
            )

    def _handle_response(self, msg: dict, addr: tuple[str, int]) -> None:
        pubkey, nonce, signature = msg.get("pubkey", ""), msg.get("nonce", ""), msg.get("signature", "")
        if not (pubkey and nonce and signature):
            return
        try:
            VerifyKey(bytes.fromhex(pubkey)).verify(nonce.encode("utf-8"), bytes.fromhex(signature))
        except (BadSignatureError, ValueError):
            return  # claimed identity doesn't match the signature -- ignore

        with self._lock:
            self.peers[pubkey] = Peer(address=addr)
        self._drain_outbox(pubkey)

    def _handle_deliver(self, msg: dict, addr: tuple[str, int]) -> None:
        to_pubkey, from_pubkey = msg.get("to", ""), msg.get("from", "")
        payload_hex, signature = msg.get("payload", ""), msg.get("signature", "")
        with self._lock:
            is_local = to_pubkey in self.identities
        if not is_local or not (from_pubkey and payload_hex and signature):
            return
        try:
            payload = bytes.fromhex(payload_hex)
            VerifyKey(bytes.fromhex(from_pubkey)).verify(payload, bytes.fromhex(signature))
        except (BadSignatureError, ValueError):
            return  # sender's signature doesn't match its claimed pubkey

        with self._lock:
            self.peers[from_pubkey] = Peer(address=addr)  # learn sender's address too
            self.inbox.append((from_pubkey, payload))

    def _handle(self, raw: bytes, addr: tuple[str, int]) -> None:
        try:
            msg = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        handler = {
            "challenge": self._handle_challenge,
            "response": self._handle_response,
            "deliver": self._handle_deliver,
        }.get(msg.get("type"))
        if handler:
            handler(msg, addr)

    # -- run loops ---------------------------------------------------------------

    def _listen_loop(self) -> None:
        self._sock.settimeout(1.0)
        while not self._stop.is_set():
            try:
                raw, addr = self._sock.recvfrom(RECV_BUFSIZE)
            except socket.timeout:
                continue
            except OSError:
                break
            self._handle(raw, addr)

    def _sweep_loop(self) -> None:
        while not self._stop.is_set():
            self.refresh_identities()
            with self._lock:
                stale = [pk for pk, p in self.peers.items() if time.time() - p.last_seen > PEER_STALE_AFTER]
                for pk in stale:
                    del self.peers[pk]
            self.challenge("*")
            self._stop.wait(CHALLENGE_INTERVAL)

    def start(self) -> None:
        self.refresh_identities()
        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._sweep_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        self._sock.close()


# -- manual test CLI ------------------------------------------------------------

def main() -> None:
    router = Router()
    router.start()
    print(f"[i] Router listening on UDP :{router.port}")
    print("Commands: identities | peers | send <from_prefix> <to_prefix|full_pubkey> <text> | quit")

    def resolve_local(ref: str) -> str | None:
        with router._lock:
            for pk in router.identities:
                if pk.startswith(ref):
                    return pk
        return None

    def resolve_target(ref: str) -> str | None:
        with router._lock:
            for pk in list(router.identities) + list(router.peers):
                if pk.startswith(ref):
                    return pk
        return ref if len(ref) == PUBKEY_HEX_LEN else None

    try:
        while True:
            line = input("> ").strip()
            if not line:
                continue
            parts = line.split(maxsplit=3)
            cmd = parts[0].lower()

            if cmd == "quit":
                break
            elif cmd == "identities":
                for pk in router.identities:
                    print(f"  {pk}")
            elif cmd == "peers":
                with router._lock:
                    for pk, peer in router.peers.items():
                        print(f"  {pk[:16]}... @ {peer.address} (seen {time.time() - peer.last_seen:.1f}s ago)")
            elif cmd == "send" and len(parts) == 4:
                from_ref, to_ref, text = parts[1], parts[2], parts[3]
                from_pk, to_pk = resolve_local(from_ref), resolve_target(to_ref)
                if not from_pk:
                    print(f"[!] '{from_ref}' doesn't match a local pod identity.")
                elif not to_pk:
                    print(f"[!] '{to_ref}' isn't a known peer/identity and isn't a full pubkey.")
                else:
                    router.send(from_pk, to_pk, text.encode("utf-8"))
                    print(f"[i] queued/sent {from_pk[:16]}... -> {to_pk[:16]}...")
            else:
                print("Commands: identities | peers | send <from_prefix> <to_prefix|full_pubkey> <text> | quit")

            while router.inbox:
                from_pubkey, payload = router.inbox.pop(0)
                print(f"\n[recv] from {from_pubkey[:16]}...: {payload.decode('utf-8', errors='replace')}")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        router.stop()


if __name__ == "__main__":
    main()
