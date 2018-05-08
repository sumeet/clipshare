from asyncio import ensure_future
import asyncio
import os
import threading
import time

import websockets

from local_clipboard import LocalClipboard
import log
from relay import Relay
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


def start_client():
    relay = Relay()

    local_clipboard = LocalClipboard.new()
    relay.add_clipboard(local_clipboard)

    websocket_handler = WebsocketHandler(relay)
    c = client(websocket_handler, WS_URL)

    asyncio.set_event_loop(local_clipboard.event_loop)
    local_clipboard.event_loop.run_until_complete(c)


if __name__ == '__main__':
    while True:
        try:
            start_client()
        except Exception as e:
            logger.info('got disconnected from the server')
            logger.debug(e)
            logger.info(f'waiting {RECONNECT_WAIT_SECONDS} before reconnecting')
            time.sleep(RECONNECT_WAIT_SECONDS)
