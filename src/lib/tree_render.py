# file: src/lib/tree_render.py

from rich.console import Console

from lib.deps.pydeps import DependencyNode

console = Console()


def color(text, color_name):
    return f"[{color_name}]{text}[/{color_name}]"


def print_tree(node, prefix="", is_last=True):

    branch = "" if prefix == "" else ("└── " if is_last else "├── ")

    if node.kind == "cycle":
        style = "purple"
    else:
        style = "yellow" if node.kind == "local" else (
            "green" if node.kind == "third_party" else "blue"
        )

    console.print(
        prefix + branch + color(node.name, style)
    )

    for index, child in enumerate(node.children):

        last = index == len(node.children) - 1

        print_tree(
            child,
            prefix + ("    " if is_last else "│   "),
            last,
        )