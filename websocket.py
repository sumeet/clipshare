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
                incoming_msg = await websocket.recv()
                logger.debug(f'receiving {log.format_obj(incoming_msg)}')
                await sock.callback(incoming_msg)


class Sock:

    # by default the callback doesn't do anything. it has to be set by the
    # relay. this should be overridden by the caller using the setter
    def __init__(self, websocket):
        self._websocket = websocket
        self._callback = lambda *args: None

    async def send_message(self, message):
        logger.debug(f'sending {log.format_obj(message)}')
        await self._websocket.send(message)

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, callback):
        self._callback = callback
