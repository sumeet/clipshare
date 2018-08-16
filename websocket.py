import asyncio
from collections import namedtuple
import log
import pickle

import chunk
from chunked_receiving import ChunkedMessageReceiver
import signals
from remote_clipboard import RemoteClipboard


logger = log.getLogger(__name__)


# by default, there's a limit of ~1MB. our payloads can be much larger than
# that, if transferring images, so let's just turn the limit off
MAX_PAYLOAD_SIZE = None


KEEPALIVE_INTERVAL_SECONDS = 30


# when running clipshare behind nginx, the server and client would seem to get
# disconnected frequently. at least on dokku's settings. adding this keepalive
# fixes the problem there. it's probably good to keep this in here. i bet it'll
# help with other configurations as well.
async def keepalive_forever(websocket):
    while True:
        await asyncio.sleep(KEEPALIVE_INTERVAL_SECONDS)
        await websocket.ping()


class Sock:

    # this is used on the server, which doesn't want to chunk the messages it's
    # relaying between the clients. the clients chunk and rejoin, while the
    # server just relays whatever's sent to it without waiting to rejoin it
    @classmethod
    def without_chunking(cls, websocket):
        return cls(websocket, NoopChunker)

    # this is used for local clients which chunk and rejoin
    @classmethod
    def with_chunking(cls, websocket):
        return cls(websocket, Chunker())

    def __init__(self, websocket, chunker):
        self._websocket = websocket
        self._chunker = chunker
        self._signaler = chunker.Signaler()

    async def send_message(self, message):
        logger.debug(f'sending {log.format_obj(message)}')
        chunks = self._chunker.chunk(message)

        first_chunk = next(chunks)
        self._signaler.begin_outgoing_transfer(first_chunk.total_chunks)
        await self._send_on_websocket(first_chunk)

        for chunk in chunks:
            await self._send_on_websocket(chunk)

    async def _send_on_websocket(self, chunk):
        await self._websocket.send(pickle.dumps(chunk))
        self._signaler.on_outgoing_chunk_sent()

    async def recv_message(self):
        complete_message = None
        while complete_message is None:
            incoming_msg = await self._websocket.recv()
            logger.debug(f'receiving {log.format_obj(incoming_msg)}')
            chunk = pickle.loads(incoming_msg)

            if chunk.is_the_first_chunk:
                self._signaler.begin_incoming_transfer(chunk.total_chunks)

            self._signaler.on_incoming_chunk_received()
            complete_message = self._chunker.receive_chunk(chunk)
        else:
            return complete_message

    @property
    def connection_details(self):
        return f'{self._websocket.host}:{self._websocket.port}'


class NoopChunker:

    # XXX: pretty sure this double pickling is super womp... but i'm tired and
    # i can't get the server to stop trying to unpickle the chunked data.
    #
    # come back to this at some point and undo the double pickling
    @classmethod
    def chunk(cls, outgoing_msg):
        yield pickle.loads(outgoing_msg)

    @classmethod
    def receive_chunk(cls, incoming_chunk):
        return pickle.dumps(incoming_chunk)

    # don't need to signal any progress for non-chunked transfers, on the
    # server
    class Signaler:
        on_outgoing_chunk_sent = lambda *args: None
        on_incoming_chunk_received = lambda *args: None
        begin_outgoing_transfer = lambda *args: None
        begin_incoming_transfer = lambda *args: None


class Chunker:

    # don't send an entire clipboard payload to the server in a single
    # websocket message. the reason being, we can't measure progress if all the
    # data is sent in a single message. we want to show a progress bar. split
    # it into chunks so we know how much we sent, and how much is remaining to
    # send
    #
    # TODO: tune this value by measuring transfer speed time
    SPLIT_SIZE_BYTES = 500_000

    def __init__(self):
        self._rejoiner = chunk.Rejoiner()

    def chunk(self, outgoing_msg):
        return chunk.Splitter(self.SPLIT_SIZE_BYTES, outgoing_msg).splits

    def receive_chunk(self, chunk):
        maybe_full_message = self._rejoiner.process_incoming_chunk(chunk)
        return maybe_full_message or None

    class Signaler:

        def __init__(self):
            self._outgoing_progress = None
            self._incoming_progress = None

        def begin_outgoing_transfer(self, total):
            self._outgoing_progress = TransferProgress(total=total, completed=0)
            logger.debug(f'signalling outgoing transfer: {self._outgoing_progress}')
            signals.outgoing_transfer.send(self._outgoing_progress)

        def on_outgoing_chunk_sent(self):
            self._outgoing_progress = self._outgoing_progress.increment_completed
            logger.debug(f'signalling outgoing transfer: {self._outgoing_progress}')
            signals.outgoing_transfer.send(self._outgoing_progress)

        def begin_incoming_transfer(self, total):
            self._incoming_progress = TransferProgress(total=total, completed=0)
            logger.debug(f'signalling incoming transfer: {self._incoming_progress}')
            signals.incoming_transfer.send(self._incoming_progress)

        def on_incoming_chunk_received(self):
            self._incoming_progress = self._incoming_progress.increment_completed
            logger.debug(f'signalling incoming transfer: {self._incoming_progress}')
            signals.incoming_transfer.send(self._incoming_progress)


class TransferProgress(namedtuple('TransferProgress', 'total completed')):

    @property
    def increment_completed(self):
        return self._replace(completed=self.completed + 1)

    @property
    def is_complete(self):
        return self.total == self.completed
