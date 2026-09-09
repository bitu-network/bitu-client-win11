# file: src/lib/deps/webdeps.py
# HTML/JS/CSS scanner

import re
from pathlib import Path

from lib.deps.models import DependencyNode


HTML_PATTERNS = [
    r'<script[^>]+src=["\']([^"\']+)["\']',
    r'<link[^>]+href=["\']([^"\']+)["\']',
    r'<img[^>]+src=["\']([^"\']+)["\']',
]

JS_PATTERNS = [
    r'import\s+.*?\s+from\s+["\']([^"\']+)["\']',
    r'import\s*["\']([^"\']+)["\']',
    r'require\(["\']([^"\']+)["\']\)',
]

CSS_PATTERNS = [
    r'@import\s+["\']([^"\']+)["\']',
    r'url\(["\']?([^"\')]+)["\']?\)',
]


def find_references(
    file: Path,
) -> list[str]:

    content = file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    references = []

    suffix = file.suffix.lower()

    if suffix == ".html":
        patterns = HTML_PATTERNS

    elif suffix == ".js":
        patterns = JS_PATTERNS

    elif suffix == ".css":
        patterns = CSS_PATTERNS

    else:
        return []

    for pattern in patterns:
        references.extend(
            re.findall(
                pattern,
                content,
            )
        )

    return references


def resolve_web_dependency(
    reference: str,
    current_file: Path,
) -> Path | None:

    # Ignore external URLs
    if (
        reference.startswith("http://")
        or reference.startswith("https://")
        or reference.startswith("//")
    ):
        return None

    candidate = (
        current_file.parent / reference
    ).resolve()

    if candidate.exists():
        return candidate

    return None


def build_web_dependency_tree(
    web_file: Path,
    root: Path,
    visited: set[Path] | None = None,
) -> DependencyNode:

    web_file = web_file.resolve()

    if visited is None:
        visited = set()

    if web_file in visited:
        return DependencyNode(
            name=web_file.name,
            path=web_file,
            kind="cycle",
        )

    visited.add(web_file)

    node = DependencyNode(
        name=str(web_file.relative_to(root)),
        path=web_file,
    )

    for reference in find_references(web_file):

        dependency = resolve_web_dependency(
            reference,
            web_file,
        )

        if dependency:

            node.children.append(
                build_web_dependency_tree(
                    dependency,
                    root,
                    visited,
                )
            )

    return node