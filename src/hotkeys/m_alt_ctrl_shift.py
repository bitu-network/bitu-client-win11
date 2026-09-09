# file: src/hotkeys/m_alt_ctrl_shift.py

import os
import sys
import webbrowser

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import LOCAL_SERVER


def open_globe_page():
    url = f"{LOCAL_SERVER}/globe/globe.html"
    webbrowser.open(url)
    print(f"Opened {url}")


if __name__ == "__main__":
    open_globe_page()

