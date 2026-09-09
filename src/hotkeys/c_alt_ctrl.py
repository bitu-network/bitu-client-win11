# file: src/hotkeys/c_alt_ctrl.py
# description: Reads file/folder paths from the clipboard, recursively collects source files from them, bundles their contents, and copies the combined context to the clipboard.
import json
import subprocess
from pathlib import Path


SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
}


def get_clipboard_text() -> str:
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-Clipboard",
        ],
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def set_clipboard_text(text: str):
    subprocess.run(
        [
            "powershell",
            "-Command",
            "Set-Clipboard -Value @'",
            text,
            "'@",
        ]
    )


def load_paths() -> list[Path]:
    raw = get_clipboard_text()

    if not raw:
        return []

    try:
        data = json.loads(raw)

        if isinstance(data, list):
            return [Path(p) for p in data]

    except json.JSONDecodeError:
        pass

    return []


def collect_files(paths: list[Path]) -> list[Path]:
    files = []

    for path in paths:

        if path.is_file():
            if path.suffix.lower() in SOURCE_EXTENSIONS:
                files.append(path)

        elif path.is_dir():
            for file in path.rglob("*"):
                if (
                    file.is_file()
                    and file.suffix.lower() in SOURCE_EXTENSIONS
                ):
                    files.append(file)

    return files


def build_context(files: list[Path]) -> str:
    sections = []

    for file in files:
        try:
            content = file.read_text(
                encoding="utf-8",
                errors="replace",
            )

            sections.append(
                "\n".join(
                    [
                        "=" * 80,
                        f"FILE: {file}",
                        "=" * 80,
                        "",
                        content,
                        "",
                    ]
                )
            )

        except Exception as e:
            sections.append(
                "\n".join(
                    [
                        "=" * 80,
                        f"FILE: {file}",
                        "=" * 80,
                        f"[FAILED TO READ: {e}]",
                        "",
                    ]
                )
            )

    return "\n".join(sections)


paths = load_paths()

if not paths:
    print("Clipboard accumulator is empty.")
    raise SystemExit(0)


files = collect_files(paths)

if not files:
    print("No source files found.")
    raise SystemExit(0)


context = build_context(files)

set_clipboard_text(context)


print(f"Copied {len(files)} files into AI context clipboard.")