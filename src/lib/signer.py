# file: src/lib/signer.py

import nacl.signing
import nacl.encoding
from pod.config import get_value

class SignerError(Exception):
    pass

def _load_private_key(key_id: str) -> nacl.signing.SigningKey:
    """Retrieve the private key from secure store by ID."""
    hex_key = get_value(key_id)
    if hex_key is None:
        raise SignerError(f"No private key found for ID '{key_id}'")
    return nacl.signing.SigningKey(bytes.fromhex(hex_key))

def get_public_key(key_id: str) -> str:
    """Return the Ed25519 public key as hex for the given key ID."""
    private_key = _load_private_key(key_id)
    return private_key.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()

def sign_message(key_id: str, message: bytes) -> bytes:
    """Sign a message using the private key identified by key_id."""
    private_key = _load_private_key(key_id)
    return private_key.sign(message).signature
