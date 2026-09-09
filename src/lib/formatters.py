# file: src/lib/formatters.py
def truncate(text: str, n: int = 12) -> str:
    """Truncate a string to n characters, adding '...' if needed."""
    return text[:n] + "..." if len(text) > n else text
