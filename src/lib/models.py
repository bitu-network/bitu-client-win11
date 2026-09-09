# file: src/lib/models.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class PeerInfo:
    pubkey: str
    socket: str
    alias: Optional[str]
    peer_dir: Path
    root: Path
