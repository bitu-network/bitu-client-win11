# file: src/cli/git_context.py

import subprocess
from pathlib import Path

from project import get_project_root
from lib.ai_context import load_ai_context, build_context


def run_git_command(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def build_git_context(project_root: Path) -> str:
    sections = []

    sections.append(
        "\n".join(
            [
                "=" * 80,
                "GIT STATUS",
                "=" * 80,
                "",
                run_git_command(["status", "--short"]),
                "",
            ]
        )
    )

    sections.append(
        "\n".join(
            [
                "=" * 80,
                "GIT DIFF",
                "=" * 80,
                "",
                run_git_command(["diff", "HEAD"]),
                "",
            ]
        )
    )

    return "\n".join(sections)


def set_clipboard_text(text: str):
    subprocess.run(
        [
            "powershell",
            "-Command",
            "$input | Set-Clipboard",
        ],
        input=text,
        text=True,
    )


project_root = get_project_root()

if project_root is None:
    print("Could not find project root.")
    raise SystemExit(0)


git_context = build_git_context(project_root)





set_clipboard_text(git_context)

print("Copied git review context to clipboard.")