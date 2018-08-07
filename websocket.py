import log

from remote_clipboard import RemoteClipboard


logger = log.getLogger(__name__)


# by default, there's a limit of ~1MB. our payloads can be much larger than
# that, if transferring images, so let's just turn the limit off
MAX_PAYLOAD_SIZE = None


class WebsocketHandler:

    def __init__(self, relay):
        self._relay = relay

    async def handle(self, websocket, path):  # yup, we're ignoring path
        logger.debug(f'connected with {websocket.host}:{websocket.port}')
        sock = Sock(websocket)
        remote_clipboard = RemoteClipboard(sock)
        with self._relay.with_clipboard(remote_clipboard):
            while True:
                await sock.callback(await sock.recv_message())


class Sock:

    # by default the callback doesn't do anything. it has to be set by the
    # relay. this should be overridden by the caller using the setter
    async def _callback(*args):
        return None

    def __init__(self, websocket):
        self._websocket = websocket

    async def send_message(self, message):
        logger.debug(f'sending {log.format_obj(message)}')
        await self._websocket.send(message)

    async def recv_message(self):
        incoming_msg = await self._websocket.recv()
        logger.debug(f'receiving {log.format_obj(incoming_msg)}')
        return incoming_msg

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, callback):
        self._callback = callback

    @property
    def connection_details(self):
        return f'{self._websocket.host}:{self._websocket.port}'
