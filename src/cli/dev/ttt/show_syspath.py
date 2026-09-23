# file: src/cli/dev/ttt/show_syspath.py

import sys
import os

def main():
    print("Python sys.path inspection:\n")
    for i, path in enumerate(sys.path):
        exists = os.path.exists(path)
        is_dir = os.path.isdir(path)
        print(f"{i:02}: {path!r} | exists: {exists} | is_dir: {is_dir}")

if __name__ == "__main__":
    main()
