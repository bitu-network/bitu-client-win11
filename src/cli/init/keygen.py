# file: src/cli/init/keygen.py

from pathlib import Path
import hashlib
import getpass
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from bip_utils import Bip39SeedGenerator, Bip39MnemonicGenerator, Bip44, Bip44Coins, Bip44Changes

from pod.config import Config

# -----------------------------
# Helper functions
# -----------------------------
def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def collect_blob_hashes(cwd: Path) -> bytes:
    """
    Collect regular files in cwd (non-directories),
    sort by filename, hash each with SHA-256,
    and concatenate the digests in order, ignoring .pod files.
    """
    blobs = sorted(
        p for p in cwd.iterdir()
        if p.is_file() and p.suffix != ".pod"
    )
    acc = b""
    for p in blobs:
        acc += hashlib.sha256(p.read_bytes()).digest()
    return acc

def derive_bip39_seed_phrase(seed_material: bytes) -> str:
    """
    Generate a BIP39 mnemonic from the SHA-256 of seed material.
    """
    seed_hash = sha256_bytes(seed_material)
    mnemonic = Bip39MnemonicGenerator().FromEntropy(seed_hash[:16])
    return mnemonic

def derive_ed25519_keypair_from_mnemonic(mnemonic: str) -> tuple[bytes, bytes]:
    """
    Deterministically derive an Ed25519 keypair from a BIP39 mnemonic.
    """
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
    seed32 = sha256_bytes(seed_bytes)  # 32 bytes
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed32)
    public_key = private_key.public_key()
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv_bytes, pub_bytes

def first_ethereum_address(mnemonic: str) -> str:
    """
    Derive the first Ethereum address from a BIP39 mnemonic.
    """
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
    bip44_mst = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
    eth_addr = bip44_mst.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0).PublicKey().ToAddress()
    return eth_addr

# -----------------------------
# Main
# -----------------------------
def main() -> None:
    cwd = Path.cwd()
    blob_hash_stream = collect_blob_hashes(cwd)
    if blob_hash_stream:
        print(f"[info] Using {len(blob_hash_stream)//32} blobs from cwd as entropy for key derivation.")
    else:
        print("[info] No blobs found in current directory; key will be derived from passphrase only.")

    # Optional passphrase as salt
    passphrase = getpass.getpass("Add optional passphrase as salt (will not echo): ")
    passphrase_bytes = passphrase.encode("utf-8") if passphrase else b""

    seed_material = blob_hash_stream + passphrase_bytes

    # Generate BIP39 mnemonic first
    mnemonic = derive_bip39_seed_phrase(seed_material)
    print("\n--- BIP39 Seed Phrase (Ethereum-compatible) ---")
    print(mnemonic)

    # Generate Ed25519 keypair from mnemonic
    priv, pub = derive_ed25519_keypair_from_mnemonic(mnemonic)
    print("\n--- Derived Ed25519 Keypair ---")
    print(f"Public key (hex): {pub.hex()}")
    print(f"Private key (hex): {priv.hex()}")

    # Derive first Ethereum address
    eth_addr = first_ethereum_address(mnemonic)
    print("\nFirst Ethereum address for this seed phrase (importable into MetaMask):")
    print(eth_addr)

    # -----------------------------
    # Store in .pod via Config
    # -----------------------------
    cfg = Config()
    cfg.set_value("mnemonic", mnemonic, encrypt=True)
    cfg.set_value("ed25519_private_key", priv.hex(), encrypt=True)
    cfg.set_value("ed25519_public_key", pub.hex())
    cfg.set_value("first_ethereum_address", eth_addr)

    print("\n[✓] Keys stored in .pod config table successfully.")

if __name__ == "__main__":
    main()
