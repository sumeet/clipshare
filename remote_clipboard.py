from collections import namedtuple
from io import BytesIO
import pickle           # lol it works

import log
import signals


logger = log.getLogger(__name__)


# don't send an entire clipboard payload to the server in a single websocket
# message. the reason being, we can't measure progress if all the data is sent
# in a single message. we want to show a progress bar. split it into chunks so
# we know how much we sent, and how much is remaining to send
#
# TODO: tune this value by measuring transfer speed time
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


class TransferProgress(namedtuple('TransferProgress', 'total completed')):

    @property
    def increment_completion_by_one(self):
        return self._replace(completed=self.completed + 1)

    @property
    def is_complete(self):
        return self.total == self.completed
