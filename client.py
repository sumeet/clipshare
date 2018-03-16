import asyncio
import threading

import websockets

from local_clipboard import LocalClipboard
from coordinator import ClipboardsCoordinator
from websocket import WebsocketHandler


async def client(websocket_handler, url):
    async with websockets.connect(url) as websocket:
        await websocket_handler.handle(websocket, "the path is ignored anyway")


if __name__ == '__main__':
    coordinator = ClipboardsCoordinator()

    local_clipboard = LocalClipboard.new()
    coordinator.add_clipboard(local_clipboard)

    websocket_handler = WebsocketHandler(coordinator)
    c = client(websocket_handler, "ws://100.114.54.75:8392")

    asyncio.set_event_loop(local_clipboard.event_loop)
    local_clipboard.event_loop.run_until_complete(c)
