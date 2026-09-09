# file: src/apps/vscode_test.py

import requests


def main():
    url = "http://127.0.0.1:8765/vscode/state"

    session = requests.Session()
    session.trust_env = False

    try:
        response = session.get(
            url,
            timeout=2,
        )

        response.raise_for_status()

        data = response.json()

        print("BIOU VSCode Extension response:")
        print(data)

    except requests.exceptions.ConnectionError:
        print("Could not connect to BIOU VSCode Extension.")
        print("Make sure VS Code is running with the extension activated.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()