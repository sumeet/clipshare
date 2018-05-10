from io import BytesIO
import pickle           # lol it works

import log


logger = log.getLogger(__name__)


MSG_SPLIT_SIZE = 500_000    # bytes


class RemoteClipboard:

    def __init__(self, sock):
        self._sock = sock
        self._message_rejoiner = MessageRejoiner()

    async def update(self, clipboard_contents):
        full_output = pickle.dumps(clipboard_contents)

        for chunk in split_message(full_output, MSG_SPLIT_SIZE):
            await self._sock.send_message(chunk)

    def set_callback_for_updates(self, callback):
        async def message_handler(msg):
            maybe_full_msg = self._message_rejoiner.process_incoming_part(msg)
            if maybe_full_msg:
                try:
                    deserialized = pickle.loads(maybe_full_msg)
                except:
                    log.info(f"couldn't deserialize joined msg: {maybe_full_msg}")
                    return
                await callback(deserialized)
            return None

        self._sock.callback = message_handler

    def __repr__(self):
        return f'<{type(self).__name__}: {self._sock.connection_details}>'


# double pickling allows me to just safely send the donemarker over the wire
def split_message(message, split_size):
    for starting_index in range(0, len(message), split_size):
        chunk = message[starting_index:starting_index+split_size]
        if chunk:
            yield pickle.dumps(chunk)
    yield pickle.dumps(donemarker)


class MessageRejoiner:

    def __init__(self):
        self._reset_received_message_buffer()

    def process_incoming_part(self, part):
        try:
            part = pickle.loads(part)
        except:
            logger.debug(f"rejoiner couldn't unpickle {log.format_obj(part)}")
            return

        if part is donemarker:
            self._received_message_buffer.seek(0)
            entire_message = self._received_message_buffer.read()
            self._reset_received_message_buffer()
            return entire_message

        self._received_message_buffer.write(part)
        return None

    def _reset_received_message_buffer(self):
        self._received_message_buffer = BytesIO()


# this won't work if the messages come out of order, which shouldn't happen in
# websockets
class donemarker(object):
    """signals the end of a multipart message"""
    pass


if __name__ == '__main__':
    def assert_equal(lhs, rhs):
        if lhs != rhs:
            raise AssertionError(f'{lhs} != {rhs}')

    rejoiner = MessageRejoiner()
    teststring = b'the quick lazy frox jumps over the lazy dog'
    chunks = list(split_message(teststring, 3))
    assert_equal(16, len(chunks))
    for i in range(15):
        assert_equal(None, rejoiner.process_incoming_part(chunks[i]))
    assert_equal(rejoiner.process_incoming_part(chunks[15]), teststring)
