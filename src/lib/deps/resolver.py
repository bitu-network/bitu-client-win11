# file: src/lib/deps/resolver.py

from pathlib import Path

from lib.deps.models import DependencyNode


def flatten_dependencies(
    node: DependencyNode,
) -> list[Path]:

    files = []
    visited = set()

    def walk(current: DependencyNode):

        if (
            current.path
            and current.path not in visited
            and current.kind in ("local", "cycle")
        ):
            visited.add(current.path)
            files.append(current.path)

        for child in current.children:
            walk(child)

    walk(node)

    return files