# file: src/lib/hotkey_context.py

from __future__ import annotations

import json
import sys


def load_context() -> dict:
    """Parses JSON context passed as the first command-line argument by the hotkey engine."""
    if len(sys.argv) > 1:
        try:
            return json.loads(sys.argv[1])
        except Exception as e:
            print(f"[ERROR] Failed to parse hotkey context JSON: {e}", file=sys.stderr)
    return {}


def get_context_fields(*fields):
    """Load only requested context fields."""

    context = load_context()

    return tuple(context.get(field) for field in fields)