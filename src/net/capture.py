# file: src/net/capture.py

from threading import Lock

from scapy.sendrecv import AsyncSniffer
from scapy.layers.inet import IP

from net.models import interfaces
from net.models import interface_stats
from net.sockets import update_socket_stats


lock = Lock()


def packet_handler(packet, iface_guid):
    size = len(packet)

    with lock:
        # interface_stats[guid]["received"] += size
        if packet.haslayer(IP):
            ip = packet[IP]

            local_ips = interfaces[iface_guid]["ip"].split(", ")

            if ip.src in local_ips:
                interface_stats[iface_guid]["sent"] += size
            elif ip.dst in local_ips:
                interface_stats[iface_guid]["received"] += size
            else:
                interface_stats[iface_guid]["received"] += size

        update_socket_stats(packet)


def start_capture():
    sniffers = []

    for guid in interfaces:

        npcap = rf"\Device\NPF_{guid}"

        try:
            sniffer = AsyncSniffer(
                iface=npcap,
                prn=lambda p, g=guid: packet_handler(p, g),
                store=False,
            )

            sniffer.start()
            sniffers.append(sniffer)

        except Exception:
            continue

    return sniffers
