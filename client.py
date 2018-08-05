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


def start_client(qapp):
    # do this first because the rest of the proggy depnds on this being established
    # as the event loop
    event_loop = QEventLoop(qapp)
    asyncio.set_event_loop(event_loop)

    relay = Relay()

    local_clipboard = LocalClipboard.new(qapp)
    relay.add_clipboard(local_clipboard)

    websocket_handler = WebsocketHandler(relay)

    ui = UI(qapp)
    signals.incoming_transfer.connect(ui.handle_incoming_transfer_progress)
    signals.outgoing_transfer.connect(ui.handle_outgoing_transfer_progress)
    ui.start()

    c = client(websocket_handler, WS_URL)

    with event_loop:
        event_loop.run_until_complete(c)


if __name__ == '__main__':
    # we need this to make it so ^c will quit the program
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    while True:
        try:
            qapp = QApplication([])
            start_client(qapp)
        except Exception as e:
            logger.info('got disconnected from the server')
            logger.exception(e)
            logger.info(f'waiting {RECONNECT_WAIT_SECONDS} before reconnecting')
            time.sleep(RECONNECT_WAIT_SECONDS)
        finally:
            qapp.quit()
