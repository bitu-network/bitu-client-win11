# file: src/cli/run/proxy.py
import asyncio
import re
import subprocess
import sys
from urllib.parse import urlparse

# Global traffic and connection statistics
stats = {"active_connections": 0, "total_bytes_up": 0, "total_bytes_down": 0}


def get_network_ips():
  """Automatically detects Windows LAN IP and active VPN adapter IP via ipconfig."""
  lan_ip = "127.0.0.1"
  vpn_ip = None
  try:
    output = subprocess.check_output("ipconfig", text=True, encoding="oem")
  except Exception:
    return lan_ip, vpn_ip

  current_adapter = ""
  for line in output.splitlines():
    if "adapter" in line.lower():
      current_adapter = line.lower()
    if "ipv4 address" in line.lower():
      match = re.search(r":\s*([0-9\.]+)", line)
      if match:
        ip = match.group(1)
        if (
            "vpn" in current_adapter
            or "wintun" in current_adapter
            or ip.startswith("100.64.")
        ):
          vpn_ip = ip
        elif ip.startswith("192.168.") or ip.startswith("10."):
          if not ip.startswith("100."):
            lan_ip = ip
  return lan_ip, vpn_ip


async def handle_client(reader, writer, vpn_local_ip):
  stats["active_connections"] += 1
  client_addr = writer.get_extra_info("peername")
  client_ip = client_addr[0] if client_addr else "Unknown"

  try:
    data = await reader.read(8192)
    if not data:
      writer.close()
      return

    first_line = data.split(b"\n")[0].decode("utf-8", errors="ignore")
    parts = first_line.split()
    if len(parts) < 2:
      writer.close()
      return

    method, url = parts[0], parts[1]

    if method == "CONNECT":
      host, port = url.split(":")
      port = int(port)
    else:
      parsed = urlparse(url)
      host = parsed.hostname
      port = parsed.port or (443 if parsed.scheme == "https" else 80)

    print(f"[+] [{client_ip}] Request -> {host}:{port} (Routing via VPN)")

    remote_reader, remote_writer = await asyncio.open_connection(
        host, port, local_addr=(vpn_local_ip, 0)
    )

    if method == "CONNECT":
      writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
      await writer.drain()
    else:
      remote_writer.write(data)
      await remote_writer.drain()
      stats["total_bytes_up"] += len(data)

    async def forward(src, dst, direction):
      try:
        while True:
          chunk = await src.read(8192)
          if not chunk:
            break
          dst.write(chunk)
          await dst.drain()
          if direction == "up":
            stats["total_bytes_up"] += len(chunk)
          else:
            stats["total_bytes_down"] += len(chunk)
      except Exception:
        pass
      finally:
        dst.close()

    await asyncio.gather(
        forward(reader, remote_writer, "up"),
        forward(remote_reader, writer, "down"),
        return_exceptions=True,
    )

  except Exception:
    pass
  finally:
    stats["active_connections"] -= 1
    writer.close()
    up_kb = stats["total_bytes_up"] / 1024
    down_kb = stats["total_bytes_down"] / 1024
    print(
        f"[-] Active: {stats['active_connections']} | Total Sent: {up_kb:.1f} KB"
        f" | Total Recv: {down_kb:.1f} KB"
    )


async def main():
  print("[*] Detecting network interfaces...")
  lan_ip, vpn_ip = get_network_ips()

  if not vpn_ip:
    print(
        "[!] Error: Could not detect active VPN IP. Make sure ExpressVPN is"
        " connected!"
    )
    sys.exit(1)

  listen_port = 3128

  print("\n" + "=" * 55)
  print("             PYTHON LAN-TO-VPN PROXY MONITOR             ")
  print("=" * 55)
  print(f"  Detected PC LAN IP : {lan_ip}")
  print(f"  Detected VPN IP    : {vpn_ip}")
  print("-" * 55)
  print("  > ENTER THESE SETTINGS ON YOUR PHONE:")
  print(f"    • Proxy Server / Host : {lan_ip}")
  print(f"    • Proxy Port          : {listen_port}")
  print(f"    • Type                : Manual / HTTP Proxy")
  print("=" * 55)
  print(f"[*] Live monitor active. Listening on port {listen_port}...\n")

  server = await asyncio.start_server(
      lambda r, w: handle_client(r, w, vpn_ip), "0.0.0.0", listen_port
  )

  async with server:
    await server.serve_forever()


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    print("\n[*] Proxy stopped.")