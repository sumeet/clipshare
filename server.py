import asyncio
import os
import websockets

from relay import Relay
from websocket import WebsocketHandler
from websocket import MAX_PAYLOAD_SIZE


if __name__ == '__main__':
    relay = Relay()
    websocket_handler = WebsocketHandler(relay)

    port = os.environ['PORT']
    start_server = websockets.serve(websocket_handler.handle, '0.0.0.0', port,
                                    max_size=MAX_PAYLOAD_SIZE)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
