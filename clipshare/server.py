import asyncio
import os
import websockets

from . import log
from . import signals
from .relay import Relay
from .remote_relay_node import RemoteRelayNode
from .websocket import MAX_PAYLOAD_SIZE
from .websocket import keepalive_forever


logger = log.get_logger(__name__)


class Server:

    def __init__(self, bind_host, port, relay):
        self.bind_host = bind_host
        self.port = port

        self._relay = relay
        self._server = None

    def start(self):
        if self._server:
            raise Exception('fatal error: server running, but tried to start')
        asyncio.ensure_future(self._start_listening())

    def stop(self):
        if self.is_active:
            self._server.close()

    @property
    def is_active(self):
        return self._server is not None

    async def _start_listening(self):
        self._server = await websockets.serve(self._handle_websocket,
                                              self.bind_host, self.port,
                                              max_size=MAX_PAYLOAD_SIZE)
        signals.server_listening.send()

    async def _handle_websocket(self, websocket, path):
        # this server doesn't look at the websocket url or path. it treats all
        # incoming requests the same
        with self._relay.with_node(RemoteRelayNode(websocket)):
            await keepalive_forever(websocket)


if __name__ == '__main__':
    bind_host = os.environ.get('BIND_HOST', '0.0.0.0')
    port = os.environ.get('PORT', 8000)
    server = Server(bind_host, port, Relay())

    server.start()
    asyncio.get_event_loop().run_forever()
