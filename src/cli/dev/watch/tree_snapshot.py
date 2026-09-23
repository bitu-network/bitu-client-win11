# file: src/cli/dev/watch/tree_snapshot.py
# description: continuously keeps a plain-text, paths-only tree of the project
# at the project root (PROJECT_TREE.txt) up to date -- meant to be read by an
# AI for a panoramic "where is everything" view without paying for file
# content. Gitignore-aware via `git ls-files --cached --others
# --exclude-standard` (the same query `git status` uses), so it needs no
# gitignore-parsing logic of its own.
#
# Lives alongside filepath_header_injector.py under cli/dev/watch/ and is
# started from __main__.py as a second background thread in the same daemon
# process (tasks.json only ever launches `python -m cli.dev.watch` once --
# this module doesn't get its own task or its own process).
#
# Runs on a plain poll loop like the header injector rather than a filesystem-
# events watcher, for the same reason: simple, dependency-free, and cheap
# enough at this project's size. The output file is only rewritten when the
# tree actually changed, so it doesn't spam mtimes/logs every poll.

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    from project import get_project_root
except ImportError:
    def get_project_root() -> Path:
        return Path(__file__).resolve().parents[4]
    
DEFAULT_OUT_DIR = "docs"
DEFAULT_OUT_NAME = "PROJECT_TREE.txt"
DEFAULT_INTERVAL = 2.0  # seconds between polls


def _tracked_paths(project_root: Path) -> list[str]:
    """Every path git would track from this root: committed + untracked-but-
    not-ignored, exactly what `git status` considers relevant. Falls back to
    a plain (non-gitignore-aware) walk if this isn't a git repo or git isn't
    on PATH.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        paths = [line for line in result.stdout.splitlines() if line]
        if paths:
            return sorted(paths)
    except (OSError, subprocess.CalledProcessError):
        pass

    skip_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
    found = []
    for path in project_root.rglob("*"):
        if path.is_file() and not any(part in skip_dirs for part in path.parts):
            found.append(path.relative_to(project_root).as_posix())
    return sorted(found)


def _build_tree(paths: list[str]) -> dict:
    """Nest flat 'a/b/c.py' paths into {'a': {'b': {'c.py': None}}}."""
    root: dict = {}
    for path in paths:
        node = root
        parts = path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None
    return root


def _render_text(node: dict, prefix: str = "") -> list[str]:
    lines = []
    entries = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0].lower()))
    for i, (name, child) in enumerate(entries):
        last = i == len(entries) - 1
        connector = "└── " if last else "├── "
        label = f"{name}/" if child is not None else name
        lines.append(f"{prefix}{connector}{label}")
        if child is not None:
            extension = "    " if last else "│   "
            lines.extend(_render_text(child, prefix + extension))
    return lines


def render(project_root: Path, fmt: str = "text") -> str:
    paths = _tracked_paths(project_root)
    tree = _build_tree(paths)
    if fmt == "json":
        return json.dumps(tree, indent=2)
    root_label = project_root.name + "/"
    return "\n".join([root_label] + _render_text(tree))


def watch_loop(project_root: Path, out_path: Path, interval: float = DEFAULT_INTERVAL) -> None:
    """Regenerate `out_path` from the current tree every `interval` seconds,
    forever. Only writes when the content actually changed. Intended to be
    run in a background thread of the watch daemon -- never exits on its own,
    so callers should mark that thread as daemon=True.
    """
    print(f"[*] Tree snapshot daemon started, writing to: {out_path}")
    last_output = None
    while True:
        try:
            output = render(project_root, "text")
            if output != last_output:
                out_path.write_text(output + "\n", encoding="utf-8")
                print(f"[+] Updated {out_path.name}")
                last_output = output
        except Exception as e:
            print(f"[!] Error updating tree snapshot: {e}", file=sys.stderr)
        time.sleep(interval)


def main() -> None:
    """Standalone one-shot use: `python -m cli.dev.watch.tree_snapshot`."""
    parser = argparse.ArgumentParser(description="Snapshot the project's file structure (paths only).")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--out", type=Path, default=None,
                         help="Write to this file instead of stdout.")
    parser.add_argument("--watch", action="store_true",
                         help="Keep running and update the file continuously instead of a single snapshot.")
    args = parser.parse_args()

    project_root = get_project_root()

    if args.watch:
        out_path = args.out or (project_root / DEFAULT_OUT_DIR / DEFAULT_OUT_NAME)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        watch_loop(project_root, out_path)
        return

    output = render(project_root, args.format)
    if args.out:
        args.out.write_text(output + "\n", encoding="utf-8")
        print(f"[+] Wrote {args.format} tree to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
