import asyncio
import os
import websockets

from relay import Relay
from remote_relay_node import RemoteRelayNode
from websocket import MAX_PAYLOAD_SIZE
from websocket import Sock
from websocket import keepalive_forever


class Server:

    def __init__(self):
        self._relay = Relay()

    async def handle_websocket(self, websocket, path):
        # this server doesn't look at the websocket url or path. it treats all
        # incoming requests the same
        with self._relay.with_node(RemoteRelayNode(websocket)):
            await keepalive_forever(websocket)


if __name__ == '__main__':
    server = Server()

    port = os.environ['PORT']
    start_server = websockets.serve(server.handle_websocket, '0.0.0.0', port,
                                    max_size=MAX_PAYLOAD_SIZE)
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(start_server)
    event_loop.run_forever()
