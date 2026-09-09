# file: src/cli/dev/report/git_changes.py

import argparse
from pathlib import Path

from lib.clipboard_utils import copy_to_clipboard
from lib.git_utils import (
    read_file_content,
    run_git,
)
from lib.project_finder import find_project_root

# Character threshold safety limit for AI chat textboxes (~15,000 chars)
SAFE_DIFF_CHAR_LIMIT = 15000


def parse_args():
    parser = argparse.ArgumentParser(
        prog="git_context",
        description="Generates a Git status and diff report for AI reviews with an interactive unified file manifest.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional paths or wildcard patterns to limit the review",
    )
    return parser.parse_args()


def get_git_status_records(git_root: Path, target_paths: list[str]) -> list[dict]:
    pathspec = ["--", *target_paths] if target_paths else []
    out = run_git(git_root, ["status", "--porcelain", *pathspec])
    if not out:
        return []

    records = []
    for line in out.splitlines():
        if len(line) > 3:
            status_code = line[:2].strip()
            file_path = line[3:].strip()
            if file_path.startswith('"') and file_path.endswith('"'):
                file_path = file_path[1:-1]
            records.append({"path": file_path, "status": status_code})
    return records


def format_status(status: str) -> str:
    return "U" if status == "??" else status


def build_initial_report(target_paths: list[str], all_records: list[dict]) -> str:
    git_root = find_project_root(Path.cwd())
    if git_root is None:
        return "No git repository found."

    current_dir = Path(__file__).parent
    git_changes_path = current_dir / "git_changes.notes.md"
    instruction = (
        git_changes_path.read_text(encoding="utf-8").strip()
        if git_changes_path.exists()
        else ""
    )

    manifest_lines = [
        "Legend: U = Untracked, M = Modified, A = Added, D = Deleted, R = Renamed",
        "ID | Status | Path",
        "--------------------------------------------------",
    ]
    for idx, rec in enumerate(all_records, 1):
        status_char = format_status(rec["status"])
        manifest_lines.append(f"{idx} | {status_char} | {rec['path']}")

    scope_info = f" (Filtered by: {', '.join(target_paths)})" if target_paths else ""
    log_pathspec = ["--", *target_paths] if target_paths else []

    return f"""
{instruction}

Path:
{git_root}{scope_info}


==================================================
UNIFIED FILE MANIFEST
==================================================

{'\n'.join(manifest_lines)}


==================================================
RECENT COMMITS
==================================================

{run_git(git_root, ["log", "--oneline", "-10", *log_pathspec])}


==================================================
SELECTED FILE DIFFS
==================================================

No file diffs loaded yet. Use the interactive prompt to request file IDs.


==================================================
END OF REPORT
==================================================
""".strip()


def build_diffs_report(
    git_root: Path, selected_records: list[dict]
) -> tuple[str, bool]:
    selected_diffs = []
    for rec in selected_records:
        file = rec["path"]
        file_path = git_root / file
        status = rec["status"]

        if status == "??" and file_path.is_file():
            content = read_file_content(file_path)
        else:
            content = run_git(git_root, ["diff", "HEAD", "--", file])
            if not content:
                content = run_git(git_root, ["diff", "--", file])
            if not content and file_path.is_file():
                content = read_file_content(file_path)

        selected_diffs.append(
            f"--------------------------------------------------\n"
            f"FILE: {file} [{format_status(status)}]\n"
            f"--------------------------------------------------\n\n"
            f"<file_payload>\n{content}\n</file_payload>"
        )

    diffs_body = "\n\n".join(selected_diffs)
    is_oversized = len(diffs_body) > SAFE_DIFF_CHAR_LIMIT

    warning_header = ""
    if is_oversized:
        warning_header = (
            "[WARNING: The requested file diffs exceed the safe character threshold "
            f"({len(diffs_body)} / {SAFE_DIFF_CHAR_LIMIT} chars). Please paste this message "
            "to the chatbot so it can ask for a smaller set of file IDs next time.]\n\n"
        )

    report_content = f"""
{warning_header}==================================================
REQUESTED FILE DIFFS ({len(selected_records)} files)
==================================================

{diffs_body}
--------------------------------------------------
[INSTRUCTION REMINDER: Do NOT generate the final COMMIT PLAN yet. If you need more file diffs, reply ONLY with a comma-separated list of missing file IDs (e.g., 3,12,19). Only generate the COMMIT PLAN when you have all necessary files.]
""".strip()

    return report_content, is_oversized


def parse_selection(selection_str: str, all_records: list[dict]) -> list[dict]:
    selected = []
    for part in selection_str.replace(",", " ").split():
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(all_records):
                selected.append(all_records[idx])
    return selected


def report_changes():
    args = parse_args()
    git_root = find_project_root(Path.cwd())
    if git_root is None:
        print("No git repository found.")
        return

    all_records = get_git_status_records(git_root, args.paths)
    if not all_records:
        print("No changes found.")
        return

    # 1. Copy initial full template to clipboard
    initial_report = build_initial_report(args.paths, all_records)
    copy_to_clipboard(initial_report)
    print(
        f"Initial report template ({len(all_records)} files in manifest) copied to clipboard."
    )

    selected_records = []

    # 2. Interactive incremental loop
    while True:
        print(
            f"\nUnified File Manifest (Currently loaded diffs: {len(selected_records)} files):"
        )
        for idx, rec in enumerate(all_records, 1):
            marker = "[x]" if rec in selected_records else "[ ]"
            print(f"  {marker} [{idx}] {rec['path']} ({format_status(rec['status'])})")
        print()

        selection = input(
            "Enter file IDs to add diffs (e.g., 1,5,8 or press Enter to finish): "
        ).strip()
        if not selection:
            break

        new_records = parse_selection(selection, all_records)
        added_count = 0
        for rec in new_records:
            if rec not in selected_records:
                selected_records.append(rec)
                added_count += 1

        if not selected_records:
            print("No valid files selected.")
            continue

        diffs_report, oversized = build_diffs_report(git_root, selected_records)
        if copy_to_clipboard(diffs_report):
            print(f"Updated diffs ({len(selected_records)} files) copied to clipboard.")
            if oversized:
                print(
                    "\n[!] WARNING: Selected diffs exceed safe textbox size limit! Please inform the AI or select fewer files next time."
                )
        else:
            print("Clipboard unavailable.")

    if selected_records:
        final_report, _ = build_diffs_report(git_root, selected_records)
        copy_to_clipboard(final_report)
        print("\nFinal diff set locked and copied to clipboard. Ready for AI review!")
    else:
        print("\nNo diffs were selected.")


if __name__ == "__main__":
    report_changes()
