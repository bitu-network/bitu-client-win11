# file: src/lib/wait_cursor.py
from __future__ import annotations
import tkinter as tk


class WaitCursor:
    """Invisible full-screen overlay that displays the waiting/spinning cursor globally."""

    def __enter__(self):
        try:
            self.root = tk.Tk()
            self.root.overrideredirect(True)
            self.root.attributes("-alpha", 0.01)
            self.root.attributes("-topmost", True)
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()
            self.root.geometry(f"{w}x{h}+0+0")
            self.root.config(cursor="watch")
            self.root.update()
        except Exception:
            self.root = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass