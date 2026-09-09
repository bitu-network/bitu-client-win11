# file: src/lib/str/tags.py

def make_tag(text: str) -> str:
    return f"[{text}]"


def prepend_prefix(text: str, tag: str) -> str:
    """
    [a] foo [b]
    -> [c][a] foo [b]
    """
    return make_tag(tag) + text


def append_prefix(text: str, tag: str) -> str:
    """
    [a] foo [b]
    -> [a][c] foo [b]
    """
    tag = make_tag(tag)

    prefix_end = text.find("] ")
    if prefix_end == -1:
        return tag + text

    return text[:prefix_end + 1] + tag + text[prefix_end + 1:]


def prepend_suffix(text: str, tag: str) -> str:
    """
    [a] foo [b]
    -> [a] foo [c][b]
    """
    tag = make_tag(tag)

    suffix_start = text.rfind(" [")
    if suffix_start == -1:
        return text + " " + tag

    return text[:suffix_start] + tag + text[suffix_start:]


def append_suffix(text: str, tag: str) -> str:
    """
    [a] foo [b]
    -> [a] foo [b][c]
    """
    return text + make_tag(tag)