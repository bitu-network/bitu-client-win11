# file: src/cli/dev/ttt/foo_bar.py
import sys

def main():
    print("All parameters passed to this script:")
    for i, arg in enumerate(sys.argv[1:], start=1):
        print(f"arg[{i}] = {arg}")

if __name__ == "__main__":
    main()
