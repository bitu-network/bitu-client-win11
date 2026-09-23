# file: src/pod/keys.py
# description: a pod's own Ed25519 identity keypair, used to authenticate it
# to peers. Lives alongside config.json under the pod's bitu dir
# (<pod>\I\-\bitu\key\), not inside config.json -- identity isn't an opt-in
# setting, so it isn't managed through pod.config. The public key is
# plaintext (peers need to read it); the private key is protected with
# Windows DPAPI, tied to the current Windows user -- no passphrase, no
# hardware security module, and no new crypto dependency beyond PyNaCl
# (already used) and pywin32 (already a project dependency via pod/blobs.py).

from __future__ import annotations

from pathlib import Path

import win32crypt
from nacl.signing import SigningKey

from .paths import BITU_DIR, PERSONAL_CONCEPTS_DIR

_KEY_REL_DIR = Path(PERSONAL_CONCEPTS_DIR) / BITU_DIR / "key"
_PUBLIC_NAME = "public"
_PRIVATE_NAME = "private.dpapi"


def key_dir(drive_root: Path) -> Path:
    """<pod>\\I\\-\\bitu\\key\\ for a given pod root."""
    return drive_root / _KEY_REL_DIR


def public_key_path(drive_root: Path) -> Path:
    return key_dir(drive_root) / _PUBLIC_NAME


def private_key_path(drive_root: Path) -> Path:
    return key_dir(drive_root) / _PRIVATE_NAME


def has_keys(drive_root: Path) -> bool:
    return public_key_path(drive_root).is_file() and private_key_path(drive_root).is_file()


def load_public_key(drive_root: Path) -> str | None:
    """This pod's public key as hex, or None if it hasn't been generated."""
    try:
        return public_key_path(drive_root).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def load_private_key(drive_root: Path) -> SigningKey | None:
    """This pod's private signing key, decrypted via DPAPI for the current
    Windows user. None if it hasn't been generated, or can't be decrypted
    (e.g. reading it under a different Windows account than generated it).
    """
    try:
        blob = private_key_path(drive_root).read_bytes()
    except OSError:
        return None
    try:
        _, raw = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    except Exception:
        return None
    return SigningKey(raw)


def generate_keys(drive_root: Path) -> str:
    """Generate a new Ed25519 keypair for this pod, overwriting any existing
    one. Returns the new public key as hex.
    """
    folder = key_dir(drive_root)
    folder.mkdir(parents=True, exist_ok=True)

    signing_key = SigningKey.generate()
    public_hex = signing_key.verify_key.encode().hex()
    encrypted = win32crypt.CryptProtectData(bytes(signing_key), None, None, None, None, 0)

    private_key_path(drive_root).write_bytes(encrypted)
    public_key_path(drive_root).write_text(public_hex, encoding="utf-8")
    return public_hex
