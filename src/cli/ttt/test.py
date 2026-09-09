# file: src/cli/ttt/test.py
import sys
from pathlib import Path


def main():
    print("✅ CLI router successfully reached endpoint!")
    print(f"  -> Executing: {Path(__file__).relative_to(Path(__file__).parents[2])}")
    print(f"  -> Arguments passed: {sys.argv[1:]}")

    # Test if sys.path was properly set by cli.py
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) in sys.path:
        print(f"✅ Project root properly injected into sys.path: {project_root}")
    else:
        print("❌ Project root is missing from sys.path!")


if __name__ == "__main__":
    main()