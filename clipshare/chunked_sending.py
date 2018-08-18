from collections import namedtuple
import math
import pickle

from cached_property import cached_property


class Message:

    def __init__(self, payload, *, split_size):
        self._payload = payload
        self._split_size = split_size

    @property
    async def full_payload(self):
        return self._payload

    @property
    async def chunks(self):
        for chunk in self._splitter.splits:
            yield chunk

    @property
    def num_chunks(self):
        return self._splitter.num_chunks

    @cached_property
    def hash(self):
        return message_hash(self._payload)

    @cached_property
    def _splitter(self):
        return Splitter(self._serialized, split_size=self._split_size)

    @cached_property
    def _serialized(self):
        return pickle.dumps(self._payload)


def message_hash(message):
    return hash(message)


class Splitter:

    @classmethod
    def split(cls, *args, **kwargs):
        return cls(*args, **kwargs).splits

    def __init__(self, message, *, split_size):
        self._message = message
        self._split_size = split_size

    @property
    def splits(self):
        for index, data in enumerate(segment(self._message, self._split_size)):
            yield self._new_chunk(index, data)

    @cached_property
    def num_chunks(self):
        return math.ceil(len(self._message) / self._split_size)

    def _new_chunk(self, chunk_index, data):
        return Chunk(message_hash=self._message_hash, chunk_index=chunk_index,
                     total_chunks=self.num_chunks, data=data)

    @cached_property
    def _message_hash(self):
        return message_hash(self._message)


def segment(string, split_size):
    for starting_index in range(0, len(string), split_size):
        yield string[starting_index:starting_index+split_size]


class Rejoiner:

    def __init__(self):
        self._chunks_by_hash = {}

    def process_incoming_chunk(self, chunk):
        if chunk.message_hash not in self._chunks_by_hash:
            self._chunks_by_hash[chunk.message_hash] = ([self._zero] *
                                                        chunk.total_chunks)

        collected_chunks = self._chunks_by_hash[chunk.message_hash]
        collected_chunks[chunk.chunk_index] = chunk.data

        if all(chunk is not self._zero for chunk in collected_chunks):
            del self._chunks_by_hash[chunk.message_hash]
            return b''.join(chunk for chunk in collected_chunks)

    class _zero: pass


class Chunk(namedtuple('Chunk', 'chunk_index total_chunks data message_hash')):

    @property
    def is_the_first_chunk(self):
        return self.chunk_index == 0

    @property
    def is_the_last_chunk(self):
        return self.chunk_index == self.total_chunks - 1
