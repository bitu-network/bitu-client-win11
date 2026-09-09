# file: src/cli/__main__.py
import os
import runpy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CLI_FOLDER = PROJECT_ROOT / "cli"


def find_script(argv):
    """Recursively match argv elements to a script in CLI_FOLDER."""
    if not argv:
        return None, []

    current_dir = CLI_FOLDER
    for i, part in enumerate(argv):
        candidate_file = current_dir / f"{part}.py"
        candidate_pkg = current_dir / part / "__main__.py"
        next_dir = current_dir / part

        if candidate_file.is_file():
            return candidate_file, argv[i + 1 :]
        elif candidate_pkg.is_file():
            return candidate_pkg, argv[i + 1 :]
        elif next_dir.is_dir():
            current_dir = next_dir
        else:
            flat_file = CLI_FOLDER / f"cli_{'_'.join(argv[: i + 1])}.py"
            if flat_file.is_file():
                return flat_file, argv[i + 1 :]
            break

    return None, argv


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: biou <command> [args...]")
        sys.exit(1)

    script_path, remaining_args = find_script(sys.argv[1:])
    if not script_path:
        print(f"[x] No matching script found for: {' '.join(sys.argv[1:])}")
        if os.name == "nt":
            input("\nPress Enter to close...")
        sys.exit(1)

    sys.argv = [str(script_path)] + remaining_args
    sys.path.insert(0, str(script_path.parent))

    has_error = False
    try:
        runpy.run_path(
            str(script_path),
            run_name="__main__",
        )
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        has_error = True
    except Exception:
        has_error = True
        raise
    finally:
        if has_error and os.name == "nt":
            input("\n[!] Completed with errors. Press Enter to close...")
