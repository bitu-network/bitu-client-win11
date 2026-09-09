# file: src/cli/generate/dummy/points.py

import argparse
import os
import sys
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
import rust_core

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Generate dummy points pipeline.")
    parser.add_argument("n", nargs="?", type=int, help="Max hop exponent (n) for 2^n tiers")
    parser.add_argument("--mode", choices=["dasymetric", "random"], help="Sampling mode")
    args, _ = parser.parse_known_args()

    db_name = "dummy_points.sqlite"
    db_exists = os.path.exists(db_name)

    regenerate_points = True

    if db_exists:
        console.print(
            f"[bold yellow]Found existing database '{db_name}' in the current directory.[/bold yellow]"
        )
        action = Prompt.ask(
            "[bold cyan]Choose an action[/bold cyan]",
            choices=["overwrite", "keep", "exit"],
            default="keep",
        )

        if action == "exit":
            console.print("[bold red]Exiting wizard.[/bold red]")
            sys.exit(0)
        elif action == "keep":
            regenerate_points = False
        elif action == "overwrite":
            regenerate_points = True

    mode = args.mode
    if regenerate_points and not mode:
        mode = Prompt.ask(
            "[bold cyan]Choose sampling mode[/bold cyan]",
            choices=["dasymetric", "random"],
            default="dasymetric",
        )
    elif not mode:
        mode = "dasymetric"

    n = args.n
    if n is None:
        n = IntPrompt.ask(
            "[bold cyan]Enter max hop exponent (n) for 2^n tiers[/bold cyan]",
            default=20,
        )

    console.print(
        f"[bold cyan]Generation configuration:[/bold cyan] "
        f"mode=[bold magenta]{mode}[/bold magenta], n={n} generates [bold green]{2**n:,}[/bold green] points."
    )

    if regenerate_points:
        console.print(
            f"[bold green]Generating tiers from r_hop=0 to {n} via Rust ({mode}) into {db_name}...[/bold green]"
        )
        rust_core.generate_and_store_points(n, db_name, mode)  # type: ignore
    else:
        console.print(
            "[dim]Skipping point generation, retaining existing points table.[/dim]"
        )

    console.print(
        "[bold bright_green]Point pipeline execution completed successfully![/bold bright_green]"
    )


if __name__ == "__main__":
    main()