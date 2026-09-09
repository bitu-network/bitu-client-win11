# file: src/cli/show/net/interfaces.py

from rich.live import Live

from net.interfaces import load_interfaces
from net.capture import start_capture
from net.display import make_interface_table

load_interfaces()
sniffers = start_capture()

try:
    with Live(make_interface_table(), refresh_per_second=1) as live:
        while True:
            live.update(make_interface_table())


finally:
    for sniffer in sniffers:
        try:
            sniffer.stop()
        except Exception:
            pass