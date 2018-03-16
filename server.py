import asyncio
import os
import websockets

from coordinator import ClipboardsCoordinator
from websocket import WebsocketHandler


if __name__ == '__main__':
    coordinator = ClipboardsCoordinator()
    websocket_handler = WebsocketHandler(coordinator)

    port = os.environ['PORT']
    start_server = websockets.serve(websocket_handler.handle, '0.0.0.0', port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
