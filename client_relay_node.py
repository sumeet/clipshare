from asyncio import ensure_future

from asyncblink import AsyncSignal

from chunked_sending import Message
import log
import signals
from transfer_progress import ProgressSignaler


# TODO: tune this value to see if it affects speed
BYTES_PER_SPLIT = 100_000


logger = log.getLogger(__name__)


class ClientRelayNode:

    def __init__(self, clipboard):
        self.new_message_signal = AsyncSignal()
        self._clipboard = clipboard
        self._progress_signaler = ProgressSignaler(signals.incoming_transfer)

    async def accept_relayed_message(self, message):
        # we receive the message here after receiving the first chunk fully. up
        # to this point, we haven't gotten the entire message.
        #
        # there's a delay between when we first hear that there's a new message
        # and when we're ready to set clipboard contents, because we have to
        # wait for several chunks to download. transmitting an image may take
        # a few seconds to transfer, and in the meantime, if you try to paste,
        # you'll end up the previous item on the clipboard.

        # clearing the clipboard in anticipation of new contents being
        # downloaded will prevent accidental pasting.
        logger.debug('got wind of a message, clearing the clipboard')
        self._clipboard.clear()
        logger.debug('actually setting the clipboard')
        ensure_future(self._broadcast_incoming_transfer_progress(message))
        self._clipboard.set(await message.full_payload)

    def start_relaying_changes(self):
        self._clipboard.new_clipboard_contents_signal.connect(
            self._handle_new_clipboard_contents_signal)
        self._clipboard.start_listening_for_changes()

    def _handle_new_clipboard_contents_signal(self, clipboard_contents):
        message = Message(payload=clipboard_contents, split_size=BYTES_PER_SPLIT)
        self.new_message_signal.send(message)

    def __repr__(self):
        return f'<{type(self).__name__}: {type(self._clipboard).__name__}>'

    async def _broadcast_incoming_transfer_progress(self, message):
        self._progress_signaler.begin_transfer(message)
        async for chunk in message.chunks:
            self._progress_signaler.on_chunk_transferred()
