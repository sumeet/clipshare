import asyncio
import pickle

from asyncblink import AsyncSignal

import log


logger = log.getLogger(__name__)


class RemoteRelayNode:

    # websocket is an instance from the websockets library
    #
    # see https://websockets.readthedocs.io/en/stable/api.html
    def __init__(self, websocket):
        self.new_message_signal = AsyncSignal()
        self._websocket = websocket

    async def accept_relayed_message(self, message):
        async for chunk in message.chunks:
            await self._websocket.send(pickle.dumps(chunk))

    def start_relaying_changes(self):
        asyncio.ensure_future(self._process_messages())

    async def _process_messages(self):
        async for message in self._chunked_message_receiver:
            self.new_message_signal.send(message)

    @property
    def _chunked_message_receiver(self):
        return ChunkedMessageReceiver(self._depickled_socket_messages)

    @property
    def _depickled_socket_messages(self):
        return (pickle.loads(msg) async for msg in self._websocket)
