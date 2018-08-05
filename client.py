from asyncio import ensure_future
import asyncio
import os
import signal
import threading
import time

from PyQt5.QtWidgets import QApplication
from quamash import QEventLoop
import websockets

from local_clipboard import LocalClipboard
import log
from relay import Relay
import signals
from ui import UI
from websocket import MAX_PAYLOAD_SIZE
from websocket import WebsocketHandler


logger = log.getLogger(__name__)


RECONNECT_WAIT_SECONDS = 5
WS_URL = os.environ['WS_URL']

KEEPALIVE_INTERVAL_SECONDS = 30


# when running clipshare behind nginx, the server and client would seem to get
# disconnected frequently. at least on dokku's settings. adding this keepalive
# fixes the problem there. it's probably good to keep this in here. i bet it'll
# help with other configurations as well.
async def keepalive_forever(websocket, interval_seconds):
    while True:
        await asyncio.sleep(interval_seconds)
        await websocket.ping()


async def client(websocket_handler, url):
    async with websockets.connect(url,  max_size=MAX_PAYLOAD_SIZE) as websocket:
        ensure_future(keepalive_forever(websocket, KEEPALIVE_INTERVAL_SECONDS))
        await websocket_handler.handle(websocket, 'the path is ignored anyway')


class Connection:

    def __init__(self, relay, ws_url):
        self._websocket_handler = WebsocketHandler(relay)
        self._ws_url = ws_url
        self._client_future = None

    def connect(self):
        if self._is_connection_active:
            raise Exception('fatal error: client running, but tried to start')

        c = client(self._websocket_handler, self._ws_url)
        self._client_future = ensure_future(c)
        self._client_future.add_done_callback(self._client_future_done)

    def disconnect(self):
        if self._is_connection_active:
            self._client_future.cancel()

    # XXX: this doesn't neccessarily mean we're connected to the server. it
    # could mean we're still trying to establish a connection
    @property
    def _is_connection_active(self):
        return self._client_future and not self._client_future.done()

    def _client_future_done(self, client_future):
        if client_future.cancelled():
            # if cancelled, that means WE cancelled it. don't reconnect
            return
        logger.info('got disconnected from the server')
        e = client_future.exception()
        if e:
            logger.exception(e)
        ensure_future(self._wait_and_reconnect())

    async def _wait_and_reconnect(self):
        logger.info(f'waiting {RECONNECT_WAIT_SECONDS} before reconnecting')
        await asyncio.sleep(RECONNECT_WAIT_SECONDS)
        self.connect()


def start_ui(qapp):
    ui = UI(qapp)
    signals.incoming_transfer.connect(ui.handle_incoming_transfer_progress)
    signals.outgoing_transfer.connect(ui.handle_outgoing_transfer_progress)
    ui.start()
    return ui


if __name__ == '__main__':
    qapp = QApplication([])

    # do this first because the rest of the proggy depnds on this being established
    # as the event loop
    event_loop = QEventLoop(qapp)
    asyncio.set_event_loop(event_loop)

    # we need this to make it so ^c will quit the program
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    relay = Relay()

    local_clipboard = LocalClipboard.new(qapp)
    relay.add_clipboard(local_clipboard)

    websocket_handler = WebsocketHandler(relay)

    ui = start_ui(qapp)

    connection = Connection(relay, WS_URL)
    connection.connect()

    with event_loop:
        event_loop.run_forever()
