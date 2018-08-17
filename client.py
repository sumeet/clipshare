from asyncio import ensure_future
import asyncio
import os
import signal

from PyQt5.QtWidgets import QApplication
from quamash import QEventLoop
import websockets

from client_relay_node import ClientRelayNode
from local_clipboard import LocalClipboard
import log
from relay import Relay
from remote_relay_node import RemoteRelayNode
import signals
from ui import UI
from websocket import MAX_PAYLOAD_SIZE
from websocket import keepalive_forever


logger = log.getLogger(__name__)


RECONNECT_WAIT_SECONDS = 5
WS_URL = os.environ['WS_URL']


class Connection:

    def __init__(self, relay, ws_url):
        self._relay = relay
        self._ws_url = ws_url
        self._websocket_future = None

    def connect(self):
        if self.is_active:
            raise Exception('fatal error: client running, but tried to start')

        signals.connection_connecting.send()

        self._websocket_future = ensure_future(self._establish_connection())
        self._websocket_future.add_done_callback(self._client_future_done)

    async def _establish_connection(self):
        async with websockets.connect(self._ws_url,
                                      max_size=MAX_PAYLOAD_SIZE) as websocket:
            signals.connection_established.send()
            with self._relay.with_node(RemoteRelayNode(websocket)):
                await keepalive_forever(websocket)

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


def start_ui(qapp, connection):
    ui = UI(qapp, connection)
    signals.incoming_transfer.connect(ui.handle_incoming_transfer_progress)
    signals.outgoing_transfer.connect(ui.handle_outgoing_transfer_progress)

    signals.connection_established.connect(ui.handle_connection_established)
    signals.connection_connecting.connect(ui.handle_connection_connecting)
    signals.connection_disconnected.connect(ui.handle_connection_disconnected)
    ui.start()
    return ui


if __name__ == '__main__':
    qapp = QApplication([])

    # do this first because the rest of the proggy depnds on this being
    # established as the event loop
    event_loop = QEventLoop(qapp)
    event_loop.set_debug(True)
    asyncio.set_event_loop(event_loop)

    # we need this to make it so ^c will quit the program
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    relay = Relay()
    with relay.with_node(ClientRelayNode(LocalClipboard.new(qapp))):
        connection = Connection(relay, WS_URL)
        connection.connect()

        ui = start_ui(qapp, connection)

        with event_loop:
                event_loop.run_forever()
