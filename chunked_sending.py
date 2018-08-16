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
        serialized = pickle.dumps(self._payload)
        for chunk in Splitter.split(serialized, split_size=self._split_size):
            yield chunk

    @cached_property
    def hash(self):
        return message_hash(self._payload)


def message_hash(message):
    return hash(message)


class Splitter:

    @classmethod
    def split(cls, message, *, split_size):
        return cls(split_size, message).splits

    def __init__(self, split_size, message):
        self._split_size = split_size
        self._message = message

    @property
    def splits(self):
        for index, data in enumerate(segment(self._message, self._split_size)):
            yield self._new_chunk(index, data)

    def _new_chunk(self, chunk_index, data):
        return Chunk(message_hash=self._message_hash, chunk_index=chunk_index,
                     total_chunks=self._total_number_of_chunks, data=data)

    @cached_property
    def _total_number_of_chunks(self):
        return math.ceil(len(self._message) / self._split_size)

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
