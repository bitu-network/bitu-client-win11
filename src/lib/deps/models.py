# file: src/lib/deps/models.py
# DependencyNode + generic traversal

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DependencyNode:
    name: str
    path: Path | None = None
    kind: str = "local"
    children: list["DependencyNode"] = field(default_factory=list)


