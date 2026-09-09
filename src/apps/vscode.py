# file: src/apps/vscode.py

from pathlib import Path

import psutil
import win32gui
import win32process


def get_active_process_name() -> str | None:
    hwnd = win32gui.GetForegroundWindow()

    if not hwnd:
        return None

    _, pid = win32process.GetWindowThreadProcessId(hwnd)

    try:
        return psutil.Process(pid).name()

    except Exception:
        return None


def is_vscode_active() -> bool:
    process = get_active_process_name()

    return process is not None and process.lower() == "code.exe"


def get_active_window_title() -> str:
    hwnd = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(hwnd)


def get_vscode_window_title() -> str | None:
    """
    Returns the active VS Code title bar text.

    Example:
        explorer.py - .py - Visual Studio Code

    This is currently used as a lightweight source of context.
    """

    if not is_vscode_active():
        return None

    return get_active_window_title()


def get_workspace_from_title(
    title: str,
) -> Path | None:
    """
    Attempts to extract the workspace folder from a VS Code title.

    This is intentionally conservative.
    If the title does not contain a clear path, return None.

    Future:
        Replace this with a VS Code API/extension based solution.
    """

    if not title:
        return None

    parts = title.split(" - ")

    for part in reversed(parts):

        path = Path(part)

        if path.exists() and path.is_dir():
            return path.resolve()

    return None


def get_active_workspace() -> Path | None:
    """
    Returns the currently opened VS Code workspace folder.
    """

    title = get_vscode_window_title()

    if title is None:
        return None

    return get_workspace_from_title(title)