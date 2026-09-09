# file: src/cli/hash_string.py

import sys
import hashlib


def hash_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    if len(sys.argv) < 2:
        print("Usage: python hash_string.py <string>")
        sys.exit(1)

    value = sys.argv[1]
    print(hash_string(value))


if __name__ == "__main__":
    main()