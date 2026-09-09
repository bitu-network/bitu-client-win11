# file: src/lib/path_matcher.py
# Description: Resolves project file queries by suffix matching and handles ambiguity.

from pathlib import Path
import sys


def find_path_matches(
    root: Path,
    query: str,
) -> list[Path]:
    """
    Find project files matching a path suffix.

    Examples:

        query:
            explorer.py

        matches:
            src/exe/explorer.py


        query:
            exe/explorer.py

        matches:
            src/exe/explorer.py


    Matching is based on the normalized path ending,
    not the absolute path and not the project-relative path.
    """

    query = query.replace("\\", "/").lower()

    matches = []

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(root)

        relative_text = relative.as_posix().lower()

        if relative_text.endswith(query):
            matches.append(path.resolve())

    return matches


def resolve_path_queries(
    root: Path,
    queries: list[str],
) -> list[Path]:
    """
    Resolve user-provided path queries into unique project files.

    Each query must match exactly one file.

    Raises:
        SystemExit:
            If a query has no matches or multiple matches.

    Returns:
        A list of resolved file paths.
    """

    resolved = []

    for query in queries:

        matches = find_path_matches(
            root,
            query,
        )

        if not matches:
            print(f"[x] No match found: {query}")
            sys.exit(1)

        if len(matches) > 1:
            print(f"[x] Multiple matches for: {query}")

            for match in matches:
                print(f"    {match}")

            sys.exit(1)

        resolved.append(matches[0])

    return resolved