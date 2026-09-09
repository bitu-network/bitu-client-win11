# file: src/net/sockets.py

from scapy.layers.inet import IP, TCP, UDP

from net.models import socket_stats


def update_socket_stats(packet):
    if not packet.haslayer(IP):
        return

    ip = packet[IP]
    size = len(packet)

    if packet.haslayer(TCP):
        protocol = "TCP"
        src_port = packet[TCP].sport
        dst_port = packet[TCP].dport

    elif packet.haslayer(UDP):
        protocol = "UDP"
        src_port = packet[UDP].sport
        dst_port = packet[UDP].dport

    else:
        return

    src = f"{protocol} {ip.src}:{src_port}"
    dst = f"{protocol} {ip.dst}:{dst_port}"

    socket_stats[src]["sent"] += size
    socket_stats[dst]["received"] += size