# file: src/cli/generate/dummy/points_random.py
import argparse
import os
import sys
import sqlite3
import math
import random
from rich.console import Console
from rich.prompt import Prompt, IntPrompt

console = Console()


def generate_and_store_points(n: int, db_name: str):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            r_hop INTEGER,
            longitude REAL,
            latitude REAL
        )
    """)
    cursor.execute("DELETE FROM points")
    
    console.print(f"[bold green]Generating tiers from r_hop=0 to {n} using equal-area spherical sampling...[/bold green]")
    
    for r_hop in range(n + 1):
        num_points = 2**r_hop
        batch_size = 50000
        generated = 0
        
        while generated < num_points:
            current_batch = min(batch_size, num_points - generated)
            batch_data = []
            for _ in range(current_batch):
                z = random.uniform(-1.0, 1.0)
                lat = math.asin(z) * (180.0 / math.pi)
                lon = random.uniform(-180.0, 180.0)
                batch_data.append((r_hop, lon, lat))
                
            cursor.executemany("INSERT INTO points (r_hop, longitude, latitude) VALUES (?, ?, ?)", batch_data)
            conn.commit()
            generated += current_batch
            
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Generate dummy points pipeline[cite: 1].")
    parser.add_argument("n", nargs="?", type=int, help="Max hop exponent (n) for 2^n tiers[cite: 1]")
    args, _ = parser.parse_known_args()

    db_name = "dummy_points.sqlite"
    db_exists = os.path.exists(db_name)

    regenerate_points = True

    if db_exists:
        console.print(
            f"[bold yellow]Found existing database '{db_name}' in the current directory[cite: 1].[/bold yellow]"
        )
        action = Prompt.ask(
            "[bold cyan]Choose an action[/bold cyan]",
            choices=["overwrite", "keep", "exit"],
            default="keep",
        )

        if action == "exit":
            console.print("[bold red]Exiting wizard[cite: 1].[/bold red]")
            sys.exit(0)
        elif action == "keep":
            regenerate_points = False
        elif action == "overwrite":
            regenerate_points = True

    n = args.n
    if n is None:
        n = IntPrompt.ask(
            "[bold cyan]Enter max hop exponent (n) for 2^n tiers[/bold cyan]",
            default=20,
        )

    console.print(
        f"[bold cyan]Generation configuration:[/bold cyan] "
        f"n={n} generates tiers from r_hop=0 to {n}."
    )

    if regenerate_points:
        console.print(
            f"[bold green]Generating tiers from r_hop=0 to {n} natively via Python into {db_name}[cite: 1]...[/bold green]"
        )
        generate_and_store_points(n, db_name)
    else:
        console.print(
            "[dim]Skipping point generation, retaining existing points table[cite: 1].[/dim]"
        )

    console.print(
        "[bold bright_green]Point pipeline execution completed successfully[cite: 1]![/bold bright_green]"
    )


if __name__ == "__main__":
    main()