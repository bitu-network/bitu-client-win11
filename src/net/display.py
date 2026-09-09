# file: src/net/display.py

from rich.table import Table

from net.models import interfaces
from net.models import interface_stats
from net.models import socket_stats

MIN_BYTES_DISPLAY = 1000


def format_bytes(value):
    units = ["B", "KB", "MB", "GB"]

    size = float(value)

    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{size:.1f} TB"


def format_signed_bytes(value):
    if value > 0:
        return f"[green]+{format_bytes(value)}[/green]"

    if value < 0:
        return f"[red]-{format_bytes(abs(value))}[/red]"

    return "0 B"


def calculate_balance(stats):
    return stats["sent"] - stats["received"]


def add_stat_columns(table):
    table.add_column("Sent")
    table.add_column("Received")
    table.add_column("Total")
    table.add_column("Balance")


def get_stat_values(stats):
    total = stats["sent"] + stats["received"]
    balance = calculate_balance(stats)

    return (
        format_bytes(stats["sent"]),
        format_bytes(stats["received"]),
        format_bytes(total),
        format_signed_bytes(balance),
    )


def get_sorted_stat_rows(source):
    rows = []


    for key, value in list(source.items()):

        stats = value["stats"] if "stats" in value else value

        total = stats["sent"] + stats["received"]

        if total < MIN_BYTES_DISPLAY:
            continue

        rows.append(
            (
                abs(calculate_balance(stats)),
                key,
                value,
            )
        )

    rows.sort(
        key=lambda row: row[0],
        reverse=True,
    )

    return rows


def make_interface_table():
    table = Table(title="Interfaces")

    table.add_column("Interface")
    table.add_column("Address")
    add_stat_columns(table)

    source = {
        guid: {
            "info": info,
            "stats": interface_stats[guid],
        }
        for guid, info in interfaces.items()
    }

    rows = []

    for _, data in get_sorted_stat_rows(source):
        info = data["info"]
        stats = data["stats"]

        table.add_row(
            info["name"],
            info["ip"],
            *get_stat_values(stats),
        )

    return table


def make_socket_table():
    table = Table(title="Sockets")

    table.add_column("Socket")
    add_stat_columns(table)

    for _, socket, stats in get_sorted_stat_rows(socket_stats):

        table.add_row(
            socket,
            *get_stat_values(stats),
        )

    return table
