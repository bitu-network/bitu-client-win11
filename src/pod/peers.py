# file: src/pod/peers.py
# description: peer CRUD for a pod's config.json (the "peers" key defined in
# pod/config.py). A peer is {"alias": str, "socket": "host:port",
# "public_key": str | None}. Peers always belong to *the pod the caller is
# currently on* -- resolved via pod.paths.pod_root(cwd), the same function
# every other pod-aware tool uses -- and are read/written exclusively through
# pod.config.load_drive_config / save_drive_config. There is deliberately no
# separate peers file or database: this module only adds list/find/mutate
# behaviour on top of the config that already exists.
#
# Failures are raised as PeerError subclasses rather than returned as None,
# so there's exactly one place that decides what each failure means and how
# it's worded -- callers (CLI included) don't re-diagnose "which of the
# possible reasons was it" themselves.

from __future__ import annotations

import re
from pathlib import Path

from .config import load_drive_config, save_drive_config
from .paths import pod_root

# host (domain or IPv4) : port
_SOCKET_RE = re.compile(r"^([a-zA-Z0-9.-]+|\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$")


class PeerError(Exception):
    """A peer command couldn't be completed. str(e) is a user-facing reason."""


class NoPodConfig(PeerError):
    def __init__(self, root: Path):
        super().__init__(f"no pod config at {root} (run 'bitu pod init' first)")
        self.root = root


class InvalidSocket(PeerError):
    def __init__(self, socket: str):
        super().__init__(f"invalid socket '{socket}' (expected host:port)")
        self.socket = socket


class AliasTaken(PeerError):
    def __init__(self, alias: str):
        super().__init__(f"alias '{alias}' already exists")
        self.alias = alias


class PeerNotFound(PeerError):
    def __init__(self, ref: str):
        super().__init__(f"no peer matching '{ref}'")
        self.ref = ref


def validate_socket(socket: str) -> str | None:
    """Validate 'host:port' (domain or IPv4) and return it normalized, or
    None if invalid. The single place socket syntax is defined -- every peer
    command validates through this rather than re-checking the pattern.
    """
    m = _SOCKET_RE.fullmatch(socket.strip())
    if not m:
        return None
    port = int(m.group(2))
    if not (1 <= port <= 65535):
        return None
    return f"{m.group(1)}:{port}"


def _current_pod(cwd: Path | None = None) -> Path:
    return pod_root(cwd if cwd is not None else Path.cwd())


def _load_or_raise(root: Path) -> dict:
    config = load_drive_config(root)
    if config is None:
        raise NoPodConfig(root)
    return config


def _find(peers: list[dict], ref: str) -> int | None:
    """Index of the peer matching `ref`, by alias, full public key, or a
    truncated (prefix) public key -- whichever the caller happens to have."""
    for i, peer in enumerate(peers):
        if peer.get("alias") == ref:
            return i
        pubkey = peer.get("public_key") or ""
        if pubkey and (pubkey == ref or pubkey.startswith(ref)):
            return i
    return None


def list_peers(cwd: Path | None = None) -> list[dict]:
    """Peers configured on the current pod. Raises NoPodConfig if the current
    directory isn't on a valid pod."""
    root = _current_pod(cwd)
    return _load_or_raise(root)["peers"]


def add_peer(socket: str, alias: str, cwd: Path | None = None) -> dict:
    """Add a peer to the current pod's config. Returns the stored peer dict.
    Raises InvalidSocket, NoPodConfig, or AliasTaken.
    """
    norm_socket = validate_socket(socket)
    if norm_socket is None:
        raise InvalidSocket(socket)

    root = _current_pod(cwd)
    config = _load_or_raise(root)

    if _find(config["peers"], alias) is not None:
        raise AliasTaken(alias)

    peer = {"alias": alias, "socket": norm_socket, "public_key": None}
    config["peers"].append(peer)
    save_drive_config(root, config)
    return peer


def remove_peer(ref: str, cwd: Path | None = None) -> None:
    """Remove a peer (matched by alias or public key/prefix) from the current
    pod's config. Raises NoPodConfig or PeerNotFound.
    """
    root = _current_pod(cwd)
    config = _load_or_raise(root)

    idx = _find(config["peers"], ref)
    if idx is None:
        raise PeerNotFound(ref)

    del config["peers"][idx]
    save_drive_config(root, config)


def set_peer_alias(ref: str, new_alias: str, cwd: Path | None = None) -> dict:
    """Rename a peer (matched by alias or public key/prefix). Returns the
    updated peer dict. Raises NoPodConfig, PeerNotFound, or AliasTaken (if
    `new_alias` already belongs to a *different* peer).
    """
    root = _current_pod(cwd)
    config = _load_or_raise(root)

    idx = _find(config["peers"], ref)
    if idx is None:
        raise PeerNotFound(ref)

    collision = _find(config["peers"], new_alias)
    if collision is not None and collision != idx:
        raise AliasTaken(new_alias)

    config["peers"][idx]["alias"] = new_alias
    save_drive_config(root, config)
    return config["peers"][idx]
