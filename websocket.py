from remote_clipboard import RemoteClipboard


# by default, there's a limit of ~1MB. our payloads can be much larger than
# that, if transferring images, so let's just turn the limit off
MAX_PAYLOAD_SIZE = None


class WebsocketHandler:

    def __init__(self, coordinator):
        self._coordinator = coordinator

    async def handle(self, websocket, path):  # yup, we're ignoring path
        print("sum1 connected")
        sock = Sock(websocket)
        remote_clipboard = RemoteClipboard(sock)
        with self._coordinator.with_clipboard(remote_clipboard):
            while True:
                incoming_msg = await websocket.recv()
                print(f'got a msg of size {len(incoming_msg)}')
                await sock.callback(incoming_msg)


class Sock:

    # by default the callback doesn't do anything. it has to be set by the
    # coordinator. this should be overridden by the caller using the setter
    def __init__(self, websocket):
        self._websocket = websocket
        self._callback = lambda *args: None

    async def send_message(self, message):
        print(f'sending a message of size {len(message)}')
        await self._websocket.send(message)

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, callback):
        self._callback = callback