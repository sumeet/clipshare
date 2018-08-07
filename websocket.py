import asyncio
import log
import pickle

import chunk
from remote_clipboard import RemoteClipboard


logger = log.getLogger(__name__)


# by default, there's a limit of ~1MB. our payloads can be much larger than
# that, if transferring images, so let's just turn the limit off
MAX_PAYLOAD_SIZE = None


class WebsocketHandler:

    def __init__(self, relay, sock_factory):
        self._relay = relay
        self._sock_factory = sock_factory

    async def handle(self, websocket, path):  # yup, we're ignoring path
        logger.debug(f'connected with {websocket.host}:{websocket.port}')
        sock = self._sock_factory(websocket)
        remote_clipboard = RemoteClipboard(sock)
        with self._relay.with_clipboard(remote_clipboard):
            while True:
                await sock.callback(await sock.recv_message())


class Sock:

    # this is used on the server, which doesn't want to chunk the messages it's
    # relaying between the clients. the clients chunk and rejoin, while the
    # server just relays whatever's sent to it.
    @classmethod
    def without_chunking(cls, websocket):
        return cls(websocket, NoopChunker)

    # this is used for local clients which chunk and rejoin
    @classmethod
    def with_chunking(cls, websocket):
        return cls(websocket, Chunker())

    # by default the callback doesn't do anything. it has to be set by the
    # relay. this should be overridden by the caller using the setter
    async def _callback(*args):
        return None

    def __init__(self, websocket, chunker):
        self._websocket = websocket
        self._chunker = chunker

    async def send_message(self, message):
        logger.debug(f'sending {log.format_obj(message)}')
        await asyncio.gather(*(self._websocket.send(c) for c in
                               self._chunker.chunk(message)))

    async def recv_message(self):
        complete_message = None
        while complete_message is None:
            incoming_chunk = await self._websocket.recv()
            logger.debug(f'receiving {log.format_obj(incoming_chunk)}')
            complete_message = self._chunker.receive_chunk(incoming_chunk)
        else:
            return complete_message

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, callback):
        self._callback = callback

    @property
    def connection_details(self):
        return f'{self._websocket.host}:{self._websocket.port}'


class NoopChunker:

    @classmethod
    def chunk(cls, outgoing_msg):
        yield outgoing_msg

    @classmethod
    def receive_chunk(cls, incoming_chunk):
        return incoming_chunk


class Chunker:

    SPLIT_SIZE = 500_000

    def __init__(self):
        self._rejoiner = chunk.Rejoiner()

    def chunk(self, outgoing_msg):
        splits = chunk.Splitter(self.SPLIT_SIZE, outgoing_msg).splits
        return map(pickle.dumps, splits)

    def receive_chunk(self, serialized_chunk):
        chunk = pickle.loads(serialized_chunk)
        maybe_full_message = self._rejoiner.process_incoming_chunk(chunk)
        return maybe_full_message or None
