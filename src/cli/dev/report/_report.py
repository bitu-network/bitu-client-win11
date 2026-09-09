# file: src/cli/dev/report/_report.py

# Description: Shared core path expansion, dependency resolution, and gitignore filtering utilities.

from pathlib import Path
import pathspec

from lib.deps.pydeps import build_dependency_tree
from lib.deps.webdeps import build_web_dependency_tree
from lib.deps.resolver import flatten_dependencies


def expand_exact_paths(
    project_root: Path,
    inputs: list[str],
    recursive: bool,
) -> list[str]:
    """Resolves exact paths and expands directories relative to CWD or project_root."""
    expanded = []

    for item in inputs:
        candidate = Path(item)
        target = None

        if (Path.cwd() / candidate).exists():
            target = (Path.cwd() / candidate).resolve()
        elif (project_root / candidate).exists():
            target = (project_root / candidate).resolve()

        if not target or not target.exists():
            expanded.append(item)
            continue

        if target.is_file():
            expanded.append(target.relative_to(project_root.resolve()).as_posix())
        elif target.is_dir():
            children = target.rglob("*") if recursive else target.glob("*")
            for child in children:
                if child.is_file():
                    expanded.append(
                        child.relative_to(project_root.resolve()).as_posix()
                    )

    return expanded


def expand_dependencies(
    project_root: Path,
    files: list[str],
) -> list[str]:
    """Expands Python and Web dependencies recursively for given files."""
    expanded = []
    import_root = project_root / "src"

    for file in files:
        path = project_root / file

        if not path.exists():
            continue

        if path.suffix.lower() == ".py":
            tree = build_dependency_tree(path, project_root, import_root)
        elif path.suffix.lower() in (".html", ".js", ".css"):
            tree = build_web_dependency_tree(path, project_root)
        else:
            continue

        for dependency in flatten_dependencies(tree):
            relative = dependency.relative_to(project_root)
            expanded.append(relative.as_posix())

    return expanded


def filter_gitignored_files(project_root: Path, files: list[str]) -> list[str]:
    """Filters out files matching the project's .gitignore patterns."""
    gitignore_path = project_root / ".gitignore"
    if not gitignore_path.exists():
        return files

    with open(gitignore_path, "r", encoding="utf-8") as f:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", f)

    return [f for f in files if not spec.match_file(f)]


