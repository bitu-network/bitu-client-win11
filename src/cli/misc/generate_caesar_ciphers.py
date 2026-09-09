# file: src/cli/misc/generate_caesar_ciphers.py


import argparse
import string


ALPHABET = string.ascii_letters


def caesar_cipher(text: str, shift: int) -> str:
    result = []

    for char in text:
        if char in ALPHABET:
            index = ALPHABET.index(char)
            result.append(ALPHABET[(index + shift) % len(ALPHABET)])
        else:
            result.append(char)

    return "".join(result)


def main():
    parser = argparse.ArgumentParser(
        description="Print all Caesar cipher shifts"
    )

    parser.add_argument(
        "text",
        help="Text to decode/encode"
    )

    args = parser.parse_args()

    for shift in range(len(ALPHABET)):
        print(f"{shift:2}: {caesar_cipher(args.text, shift)}")


if __name__ == "__main__":
    main()