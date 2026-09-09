# file: src/lib/hotkey_context.py

import json
import sys


def load_context() -> dict:
    """Load full context passed from the hotkey router."""

    if len(sys.argv) > 1:
        return json.loads(sys.argv[1])

    return {}


def get_context_fields(*fields):
    """Load only requested context fields."""

    context = load_context()

    return tuple(context.get(field) for field in fields)