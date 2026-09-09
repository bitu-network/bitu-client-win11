# file: src/lib/clipboard.py
# Description: Provides clipboard read/write helpers.

import win32clipboard


def set_clipboard_text(text: str):
    win32clipboard.OpenClipboard()

    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(
            text,
            win32clipboard.CF_UNICODETEXT,
        )

    finally:
        win32clipboard.CloseClipboard()
