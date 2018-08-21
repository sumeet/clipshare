import asyncio
import os
import websockets

from .relay import Relay
from .remote_relay_node import RemoteRelayNode
from .websocket import MAX_PAYLOAD_SIZE
from .websocket import keepalive_forever


class Server:

    def __init__(self, relay):
        self._relay = relay

    async def serve(self, bind_host, port):
        await websockets.serve(self._handle_websocket, bind_host, port,
                               max_size=MAX_PAYLOAD_SIZE)

    async def _handle_websocket(self, websocket, path):
        # this server doesn't look at the websocket url or path. it treats all
        # incoming requests the same
        with self._relay.with_node(RemoteRelayNode(websocket)):
            await keepalive_forever(websocket)


if __name__ == '__main__':
    server = Server(Relay())
    bind_host = os.environ.get('BIND_HOST', '0.0.0.0')
    port = os.environ.get('PORT', 8000)

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(server.serve(bind_host, port))
    event_loop.run_forever()
