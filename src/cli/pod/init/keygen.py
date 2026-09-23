# file: src/cli/pod/init/keygen.py
# description: interactive wizard for src/cli/pod/init.py. Generates this
# pod's Ed25519 identity keypair (see pod.keys: DPAPI-protected private key,
# plaintext public key) -- run via init.py, but works standalone too, falling
# back to detecting its own pod root from cwd.

from __future__ import annotations

from pathlib import Path

from pod.keys import generate_keys, has_keys, public_key_path
from pod.paths import pod_root


def _drive_root() -> Path:
    injected = globals().get("DRIVE_ROOT")
    if injected is not None:
        return injected
    return pod_root(Path.cwd())


def main():
    drive_root = _drive_root()

    if has_keys(drive_root):
        choice = input(
            f"[!] Keys already exist at {public_key_path(drive_root).parent}.\n"
            "Do you want to (A)bort or (O)verwrite -- this invalidates this "
            "pod's identity to any peer that already trusts it? [A/O]: "
        ).strip().upper()
        if choice != "O":
            print("[i] Keeping existing keys.")
            return

    public_hex = generate_keys(drive_root)
    print(f"[\u2713] Generated new identity. Public key: {public_hex}")


if __name__ == "__main__":
    main()
