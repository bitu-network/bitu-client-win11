# file: src/net/interfaces.py

from scapy.arch.windows import get_windows_if_list

from net.models import interfaces


def load_interfaces():
    interfaces.clear()

    for iface in get_windows_if_list():
        if not iface.get("ips"):
            continue

        interfaces[iface["guid"]] = {
            "name": iface["name"],
            "ip": ", ".join(iface["ips"]),
        }

    return interfaces