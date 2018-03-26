import asyncio
import os
import threading
import time

import websockets

from local_clipboard import LocalClipboard
from coordinator import ClipboardsCoordinator
from websocket import MAX_PAYLOAD_SIZE
from websocket import WebsocketHandler


RECONNECT_WAIT_SECONDS = 5
WS_URL = os.environ['WS_URL']


async def client(websocket_handler, url):
    async with websockets.connect(url,  max_size=MAX_PAYLOAD_SIZE) as websocket:
        await websocket_handler.handle(websocket, 'the path is ignored anyway')


def start_client():
    coordinator = ClipboardsCoordinator()

    local_clipboard = LocalClipboard.new()
    coordinator.add_clipboard(local_clipboard)

    websocket_handler = WebsocketHandler(coordinator)
    c = client(websocket_handler, WS_URL)

    asyncio.set_event_loop(local_clipboard.event_loop)
    local_clipboard.event_loop.run_until_complete(c)


if __name__ == '__main__':
    while True:
        try:
            start_client()
        except Exception as e:
            print('got disconnected from the server')
            print(e)
            print(f'waiting {RECONNECT_WAIT_SECONDS} before reconnecting')
            time.sleep(RECONNECT_WAIT_SECONDS)
