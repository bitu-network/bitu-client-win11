# file: src/lib/context_finder.py

from dataclasses import dataclass, field
from pathlib import Path

import win32gui
import win32process
import win32api
import win32con

from apps.explorer import get_active_explorer_info


@dataclass
class ActiveContext:
    application: str | None = None
    window_title: str | None = None
    folder_path: Path | None = None
    selected_items: list[Path] = field(default_factory=list)


def get_active_application() -> tuple[str | None, str | None]:
    """
    Returns the active application's executable name and window title.
    """

    hwnd = win32gui.GetForegroundWindow()

    if not hwnd:
        return None, None

    _, pid = win32process.GetWindowThreadProcessId(hwnd)

    try:
        process = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            pid,
        )

        exe = win32process.GetModuleFileNameEx(process, 0)
        title = win32gui.GetWindowText(hwnd)

        return Path(exe).name.lower(), title

    except Exception:
        return None, win32gui.GetWindowText(hwnd)


def get_active_context() -> ActiveContext:
    """
    Detects current user context.

    Explorer-specific information is only collected
    when the active application is File Explorer.
    """

    application, title = get_active_application()

    # print("Detected application:", application)

    context = ActiveContext(
        application=application,
        window_title=title,
    )

    if application == "explorer.exe":
        folder, selected = get_active_explorer_info()

        context.folder_path = folder
        context.selected_items = selected

    return context
