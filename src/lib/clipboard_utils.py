# file: src/lib/clipboard_utils.py

import pyperclip


def copy_to_clipboard(content: str) -> bool:
    """Safely attempt to copy content to the system clipboard.

    Returns True if successful, False if headless or no clipboard utility exists.
    """
    try:
        pyperclip.copy(content)
        return True
    except Exception:
        return False