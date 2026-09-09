# file: src/net/models.py

from collections import defaultdict


def make_counter():
    return {
        "sent": 0,
        "received": 0,
    }


interface_stats = defaultdict(make_counter)
socket_stats = defaultdict(make_counter)

interfaces = {}