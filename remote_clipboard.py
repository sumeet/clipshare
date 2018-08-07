from collections import namedtuple
from io import BytesIO
import pickle           # lol it works

import log
import signals


logger = log.getLogger(__name__)


MSG_SPLIT_SIZE = 500_000


class RemoteClipboard:

    def __init__(self, sock):
        self._sock = sock

    async def update(self, clipboard_contents):
        serialized_clipboard_contents = pickle.dumps(clipboard_contents)
        await self._sock.send_message(serialized_clipboard_contents)

    def set_callback_for_updates(self, callback):
        async def message_handler(serialized_clipboard_contents):
            clipboard_contents = pickle.loads(serialized_clipboard_contents)
            await callback(clipboard_contents)
        self._sock.callback = message_handler

    def __repr__(self):
        return f'<{type(self).__name__}: {self._sock.connection_details}>'
