# file: src/lib/deps/pydeps.py
# Python AST scanner

import ast
import sys

from pathlib import Path

from lib.deps.models import DependencyNode


def find_imports(py_file: Path) -> list[str]:
    with py_file.open(
        "r",
        encoding="utf-8",
    ) as f:
        tree = ast.parse(
            f.read(),
            filename=str(py_file),
        )

    imports = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for item in node.names:
                imports.append(item.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def resolve_local_import(
    module_name: str,
    import_root: Path,
) -> Path | None:

    parts = module_name.split(".")

    current = import_root

    for part in parts:

        py_file = current / f"{part}.py"

        if py_file.exists():
            return py_file.resolve()

        folder = current / part

        if folder.is_dir():
            current = folder

        else:
            return None

    return None


def is_stdlib(module_name: str) -> bool:
    return module_name.split(".")[0] in sys.stdlib_module_names


def build_dependency_tree(
    py_file: Path,
    root: Path,
    import_root: Path,
    visited: set[Path] | None = None,
) -> DependencyNode:

    py_file = py_file.resolve()

    if py_file.suffix.lower() != ".py":
        return DependencyNode(
            name=str(py_file.relative_to(root)),
            path=py_file,
            kind="non_python",
        )

    if visited is None:
        visited = set()

    if py_file in visited:
        return DependencyNode(
            name=py_file.name,
            path=py_file,
            kind="cycle",
        )

    visited.add(py_file)

    node = DependencyNode(
        name=str(py_file.relative_to(root)),
        path=py_file,
    )

    local = []
    third_party = []
    stdlib = []

    for module in find_imports(py_file):

        dependency = resolve_local_import(
            module,
            import_root,
        )

        if dependency:
            local.append(dependency)

        elif is_stdlib(module):
            stdlib.append(module)

        else:
            third_party.append(module)

    for dependency in local:
        node.children.append(
            build_dependency_tree(
                dependency,
                root,
                import_root,
                visited,
            )
        )

    for module in third_party:
        node.children.append(
            DependencyNode(
                name=module,
                kind="third_party",
            )
        )

    for module in stdlib:
        node.children.append(
            DependencyNode(
                name=module,
                kind="stdlib",
            )
        )

    return node
