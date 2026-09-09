# file: src/cli/misc/hue.py
import argparse
import os
import webbrowser


def main():
    parser = argparse.ArgumentParser(description="Visual Language Gradient Tester")
    parser.add_argument("n", type=int, nargs="?", help="Number of solid color blocks")
    args = parser.parse_args()

    html_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "hue.html")
    )
    url = f"file://{html_path}"
    if args.n is not None:
        url += f"?n={args.n}"

    webbrowser.open(url)


if __name__ == "__main__":
    main()