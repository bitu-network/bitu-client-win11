# file: src/cli/stun_probe.py

import socket
import struct
import secrets

STUN_SERVER = "stun.cloudflare.com"
STUN_PORT = 3478


def create_stun_binding_request():
    # STUN header:
    # Message Type: Binding Request (0x0001)
    # Message Length: 0
    # Magic Cookie: 0x2112A442
    # Transaction ID: 96 bits

    transaction_id = secrets.token_bytes(12)

    header = struct.pack("!HHI12s", 0x0001, 0, 0x2112A442, transaction_id)

    return header, transaction_id


def parse_stun_response(data, transaction_id):
    _, length, cookie = struct.unpack("!HHI", data[:8])

    if cookie != 0x2112A442:
        raise Exception("Invalid STUN response")

    offset = 20

    while offset < 20 + length:
        attr_type, attr_len = struct.unpack("!HH", data[offset : offset + 4])

        value = data[offset + 4 : offset + 4 + attr_len]

        # XOR-MAPPED-ADDRESS
        if attr_type == 0x0020:
            family = value[1]

            if family == 0x01:  # IPv4
                xport = struct.unpack("!H", value[2:4])[0]
                port = xport ^ (0x2112)

                raw_ip = value[4:8]

                cookie_bytes = struct.pack("!I", 0x2112A442)

                ip_bytes = bytes(a ^ b for a, b in zip(raw_ip, cookie_bytes))

                ip = socket.inet_ntoa(ip_bytes)

                return ip, port

        offset += 4 + attr_len

    return None


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)

    request, txid = create_stun_binding_request()

    print("Contacting STUN server...")

    sock.sendto(request, (STUN_SERVER, STUN_PORT))

    response, addr = sock.recvfrom(2048)

    result = parse_stun_response(response, txid)
    if result is None:
        raise Exception("STUN response did not contain mapped address")

    print()
    print("STUN server sees:")
    print("-----------------")
    print("Public IP :", result[0])
    print("Public port:", result[1])
    print()
    print("Local socket:")
    print(sock.getsockname())


if __name__ == "__main__":
    main()
