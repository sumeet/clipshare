import pickle           # lol it works

import log


logger = log.getLogger(__name__)


class RemoteClipboard:

    def __init__(self, sock):
        self._sock = sock

    async def update(self, clipboard_contents):
        output = pickle.dumps(clipboard_contents)
        await self._sock.send_message(output)

    def set_callback_for_updates(self, callback):
        def message_handler(msg):
            try:
                deserialized = pickle.loads(msg)
            except:
                logger.debug(f"couldn't unpickle {log.format_obj(msg)}")
                return
            return callback(deserialized)

        self._sock.callback = message_handler

    def __repr__(self):
        return f'<{type(self).__name__}: {self._sock.connection_details}>'
