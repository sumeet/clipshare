import asyncio
import pickle

from asyncblink import AsyncSignal

from .chunked_receiving import ChunkedMessageReceiver
from . import log
from . import signals
from .transfer_progress import ProgressSignaler


logger = log.getLogger(__name__)


class RemoteRelayNode:

    # websocket is an instance from the websockets library
    #
    # see https://websockets.readthedocs.io/en/stable/api.html
    def __init__(self, websocket):
        self.new_message_signal = AsyncSignal()
        self._websocket = websocket
        self._progress_signaler = ProgressSignaler(signals.outgoing_transfer)

    async def accept_relayed_message(self, message):
        self._progress_signaler.begin_transfer(message)
        async for chunk in message.chunks:
            await self._websocket.send(pickle.dumps(chunk))
            self._progress_signaler.on_chunk_transferred()

    def start_relaying_changes(self):
        asyncio.ensure_future(self._process_messages())

    async def _process_messages(self):
        async for message in self._chunked_message_receiver.received_messages:
            self.new_message_signal.send(message)

    @property
    def _chunked_message_receiver(self):
        return ChunkedMessageReceiver(self._depickled_socket_messages)

    @property
    async def _depickled_socket_messages(self):
        async for msg in self._websocket:
            yield pickle.loads(msg)

    def __repr__(self):
        return (f'<{type(self).__name__}: '
                f'{self._websocket.host}:{self._websocket.port}>')
