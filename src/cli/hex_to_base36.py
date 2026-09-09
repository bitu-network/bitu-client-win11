# file: src/cli/hex_to_base36.py

import sys


BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def hex_to_base36(hex_string: str) -> str:
    number = int(hex_string, 16)

    if number == 0:
        return "0"

    result = []

    while number:
        number, remainder = divmod(number, 36)
        result.append(BASE36[remainder])

    return "".join(reversed(result))


def main():
    if len(sys.argv) < 2:
        print("Usage: python hex_to_base36.py <hex>")
        sys.exit(1)

    value = sys.argv[1].strip()

    if value.startswith("0x"):
        value = value[2:]

    print(hex_to_base36(value))


if __name__ == "__main__":
    main()