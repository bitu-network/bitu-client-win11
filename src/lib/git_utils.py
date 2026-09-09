# file: src/lib/git_utils.py

from pathlib import Path
import subprocess


def run_git(git_root: Path, args: list[str]) -> str:
    """Run a Git command in the context of the git_root directory."""
    result = subprocess.run(
        ["git", *args],
        cwd=git_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def get_untracked_files(
    git_root: Path, target_paths: list[str] | None = None
) -> list[str]:
    """Retrieve relative paths of untracked files and directories, optionally filtered by target paths."""
    args = ["ls-files", "--others", "--exclude-standard"]
    if target_paths:
        args.extend(["--", *target_paths])

    output = run_git(git_root, args)
    return output.splitlines() if output else []


def build_untracked_summary(
    git_root: Path, target_paths: list[str] | None = None
) -> str:
    """Generate a summary of untracked items, handling files and directories safely."""
    files = get_untracked_files(git_root, target_paths)

    if not files:
        return "No untracked files."

    lines = []
    for file in files:
        path = git_root / file

        if not path.exists():
            continue

        if path.is_file():
            size = f"{path.stat().st_size} bytes"
            ext = path.suffix or "<no extension>"
            lines.append(f"- {file} | {ext} | {size}")
        elif path.is_dir():
            lines.append(f"- {file}/ | <directory>")

    return "\n".join(lines)


def read_file_content(path: Path) -> str:
    """Safely read content from a file path with fallback error handling."""
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        return f"<could not read file: {e}>"