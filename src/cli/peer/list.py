# file: src/cli/peer/list.py
import sys
from pod.peers import get_peer_list

def print_table(table):
    headers = ["ALIAS", "PUBKEY", "SOCKET", "TLS", "LAST SEEN"]
    if not table:
        print("[info] No peers found.")
        return
    col_widths = [max(len(str(row[i])) for row in table + [headers]) for i in range(len(headers))]
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-"*w for w in col_widths)
    print(header_line)
    print(sep_line)
    for row in table:
        print(" | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))))

def main():
    table = get_peer_list()
    if table is None:
        sys.exit(1)
    print_table(table)

if __name__ == "__main__":
    main()
