from asyncio import ensure_future
import asyncio
import os
import signal
import sys

from PyQt5.QtWidgets import QApplication
from quamash import QEventLoop
import websockets

from .client_relay_node import ClientRelayNode
from .local_clipboard import LocalClipboard
from . import log
from .relay import Relay
from .remote_relay_node import RemoteRelayNode
from . import signals
from .ui import UI
from .websocket import MAX_PAYLOAD_SIZE
from .websocket import keepalive_forever


logger = log.getLogger(__name__)


RECONNECT_WAIT_SECONDS = 5
CONNECTION_ESTABLISH_TIMEOUT = 7


class Client:

    def __init__(self, ws_url, relay):
        self.ws_url = ws_url

        self._relay = relay
        self._websocket_future = None

    def connect(self):
        if self.is_active:
            raise Exception('fatal error: client running, but tried to start')

        signals.connection_connecting.send()

        self._websocket_future = ensure_future(self._establish_connection())
        self._websocket_future.add_done_callback(self._client_future_done)

    async def _establish_connection(self):
        connect_fut = websockets.connect(self.ws_url, max_size=MAX_PAYLOAD_SIZE)
        websocket = None
        try:
            websocket = await asyncio.wait_for(connect_fut, timeout=CONNECTION_ESTABLISH_TIMEOUT)
        except asyncio.TimeoutError:
            logger.debug(f'timed out connecting to {self.ws_url}')
            return

        try:
            signals.connection_established.send()
            with self._relay.with_node(RemoteRelayNode(websocket)):
                await keepalive_forever(websocket)
        finally:
            await websocket.close()

    def disconnect(self):
        logger.info('requested disconnect: disconnecting from server')
        if self.is_active:
            self._websocket_future.cancel()

    # XXX: this doesn't neccessarily mean we're connected to the server. it
    # could mean we're still trying to establish a connection
    @property
    def is_active(self):
        return self._websocket_future and not self._websocket_future.done()

    def _client_future_done(self, client_future):
        signals.connection_disconnected.send()

        if client_future.cancelled():
            # if cancelled, that means WE cancelled it. don't reconnect
            return

        # otherwise, we were disconnected unexpectedly. try to reconnect
        logger.info('got disconnected from the server unexpectedly')
        e = client_future.exception()
        if e:
            try:
                raise e
            except:
                logger.exception(e)
        ensure_future(self._wait_and_reconnect())

    async def _wait_and_reconnect(self):
        logger.info(f'waiting {RECONNECT_WAIT_SECONDS} before reconnecting')
        await asyncio.sleep(RECONNECT_WAIT_SECONDS)
        self.connect()
