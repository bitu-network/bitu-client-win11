# file: src/cli/stun_node.py

import asyncio
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import websockets


HTTP_PORT = 8080
WS_PORT = 8765


async def websocket_handler(websocket):
    print("Browser connected")

    await websocket.send(
        "hello from stun_node.py"
    )

    async for message in websocket:
        print(
            "Received from browser:",
            message
        )


async def websocket_server():
    async with websockets.serve(
        websocket_handler,
        "0.0.0.0",
        WS_PORT
    ):
        print(
            f"WebSocket running on {WS_PORT}"
        )

        await asyncio.Future()


def start_websocket():
    asyncio.run(
        websocket_server()
    )


def main():

    threading.Thread(
        target=start_websocket,
        daemon=True
    ).start()


    http = HTTPServer(
        ("0.0.0.0", HTTP_PORT),
        SimpleHTTPRequestHandler
    )

    print(
        f"Open client.html through http://localhost:{HTTP_PORT}"
    )

    http.serve_forever()


if __name__ == "__main__":
    main()