# file: src/cli/dev/report/pydeps_tree.py
# Description: Displays the recursive local, third-party, and standard-library dependency tree of a Python file.

import sys
from pathlib import Path

from lib.path_matcher import resolve_path_queries
from lib.deps.pydeps import build_dependency_tree
from lib.project_finder import find_project_root
from lib.tree_render import print_tree


def main():

    if len(sys.argv) != 2:
        print("usage: biou dev dependencies <file-pattern>")
        return

    root = find_project_root(Path.cwd())

    if root is None:
        print("[x] project root not found")
        return

    target = resolve_path_queries(
        root,
        [sys.argv[1]],
    )[0]

    tree = build_dependency_tree(
        target,
        root,
        root / "src",
    )

    print_tree(tree)


if __name__ == "__main__":
    main()