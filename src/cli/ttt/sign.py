# file: src/cli/ttt/sign.py

import time
from lib import signer
import nacl.encoding

def make_signed_ping() -> dict[str, str]:
    ts = str(int(time.time()))
    message = (ts + signer.get_public_key()).encode()
    signature = signer.sign_message(message)
    signature_hex = nacl.encoding.HexEncoder.encode(signature).decode()

    return {
        "timestamp": ts,
        "public_key": signer.get_public_key(),
        "signature": signature_hex
    }

if __name__ == "__main__":
    print(make_signed_ping())
