# file: src/cli/dev/report/context.py
import argparse
from pathlib import Path
import pathspec

from lib.project_finder import find_project_root
from lib.clipboard import set_clipboard_text


from lib.file_reader import read_file_content
from cli.dev.report._report import expand_exact_paths, expand_dependencies


def build_context(
    project_root: Path,
    notes: list[str],
    files: list[str],
) -> str:
    """Formats the raw context payload from files and static notes."""
    sections = []
    if notes:
        sections.extend(
            [
                "## STATIC CONTEXT NOTES",
                "",
                *[f"- {note}" for note in notes],
                "",
                "---",
                "",
            ]
        )

    sections.append(
        "\n".join(
            [
                "# AI PROJECT CONTEXT",
                "",
                f"Project: {project_root}",
                "",
                "Included files:",
                *[f"- {file}" for file in files],
                "",
                "---",
                "",
            ]
        )
    )

    for file in files:
        path = project_root / file

        if not path.exists():
            sections.append(
                "\n".join(
                    [
                        f"## FILE: {file}",
                        "",
                        "[FILE DOES NOT EXIST]",
                        "",
                    ]
                )
            )
            continue

        suffix = path.suffix.lstrip(".")
        sections.append(
            "\n".join(
                [
                    f"## FILE: {file}",
                    "",
                    f"```{suffix}",
                    read_file_content(path),
                    "```",
                    "",
                ]
            )
        )

    return "\n".join(sections)


def collect_context_files(
    project_root: Path,
    input_paths: list[str],
    include_static: bool,
    include_deps: bool,
    recursive: bool,
) -> tuple[list[str], list[str]]:
    """Helper to orchestrate path expansion, static context loading, and dependency tree generation."""
    files = expand_exact_paths(project_root, input_paths, recursive)
    notes = []

    if include_static:
        current_dir = Path(__file__).parent

        # Read static project instructions directly from context.md
        context_md_path = current_dir / "context.md"
        if context_md_path.exists():
            instruction = context_md_path.read_text(encoding="utf-8").strip()
            if instruction:
                notes.append(instruction)

        # Read static file list directly from context.files.md
        core_files_path = current_dir / "context.files.md"
        if core_files_path.exists():
            for line in core_files_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    if stripped.startswith(("- ", "* ")):
                        stripped = stripped[2:].strip()
                    if stripped:
                        files.append(stripped)

    files = list(dict.fromkeys(files))

    if include_deps:
        dependency_files = expand_dependencies(project_root, files)
        files.extend(dependency_files)
        files = list(dict.fromkeys(files))

    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
        files = [f for f in files if not spec.match_file(f)]

    return notes, files


def print_loaded_files(files: list[str]):
    print("\nLoaded files:")
    for file in files:
        print(f"\033[33m{file}\033[0m")
    print()


def main():
    parser = argparse.ArgumentParser(description="Build AI context from exact paths.")
    parser.add_argument("files", nargs="*", help="Exact files or directories.")
    parser.add_argument("-s", "--include-static-context", action="store_true")
    parser.add_argument("-d", "--include-dependencies", action="store_true")
    parser.add_argument("-r", "--recursive", action="store_true")

    args = parser.parse_args()
    project_root = find_project_root(Path.cwd())
    if not project_root:
        print("Could not find project root.")
        return

    notes, files = collect_context_files(
        project_root,
        args.files,
        include_static=args.include_static_context,
        include_deps=args.include_dependencies,
        recursive=args.recursive,
    )

    context = build_context(project_root, notes, files)
    print_loaded_files(files)
    set_clipboard_text(context)
    print(f"Copied {len(files)} files into AI context clipboard.")


if __name__ == "__main__":
    main()
