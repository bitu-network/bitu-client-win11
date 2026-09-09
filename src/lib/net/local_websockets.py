# file: src/lib/net/local_websockets.py
import os
import json
import asyncio
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import websockets


class LocalWS:
    def __init__(self, host="localhost", ws_port=8765, http_port=None, static_dir=None):
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        self.static_dir = static_dir
        self.clients = set()
        self.loop = None

    async def _ws_handler(self, websocket):
        self.clients.add(websocket)
        try:
            await websocket.send(json.dumps(self.initial_data()))
            async for msg in websocket:
                await self.on_message(msg)
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, data):
        if not self.clients:
            return
        msg = json.dumps(data)
        await asyncio.gather(*(c.send(msg) for c in self.clients))

    async def on_message(self, msg):
        """Override in subclass or assign a coroutine to handle incoming messages"""
        pass

    def initial_data(self):
        """Override to return initial data for clients"""
        return {}

    def _start_ws_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._ws_main())

    async def _ws_main(self):
        async with websockets.serve(self._ws_handler, self.host, self.ws_port):
            await asyncio.Future()  # run forever

    def start_ws(self):
        threading.Thread(target=self._start_ws_loop, daemon=True).start()

    def start_http(self):
        if not self.http_port or not self.static_dir:
            return

        static_dir = self.static_dir  # capture in local variable

        class StaticHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=static_dir, **kwargs)

        httpd = ThreadingHTTPServer((self.host, self.http_port), StaticHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def send(self, data):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(data), self.loop)
