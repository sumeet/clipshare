import asyncio

from chunk import Splitter


class ChunkedMessageReceiver:

    def __init__(self, async_chunk_generator):
        self._async_chunk_generator = async_chunk_generator
        self._rejoiner = Rejoiner()
        self._queue = asyncio.Queue()

    @property
    async def received_messages(self):
        asyncio.ensure_future(self._process_messages())
        message = await self._queue.get()
        while message is not StopIteration:
            yield message
            message = await self._queue.get()

    async def _process_messages(self):
        async for chunk in self._async_chunk_generator:
            new_message = self._rejoiner.process_incoming_chunk(chunk)
            if new_message:
                await self._queue.put(new_message)
        # XXX: in production, we should never actually finish iterating the
        # socket, because it's an endless stream of messages. but we're testing
        # with a finite generator, so let's halt iteration when that happens
        await self._queue.put(StopIteration)


# async version of the rejoiner in chunk.py
class Rejoiner:

    def __init__(self):
        self._messages_by_hash = {}

    def process_incoming_chunk(self, chunk):
        if chunk.message_hash not in self._messages_by_hash:
            self._messages_by_hash[chunk.message_hash] = \
                ChunkedMessage(chunk.total_chunks)
            received_first_chunk_of_new_message = True
        else:
            received_first_chunk_of_new_message = False

        chunked_message = self._messages_by_hash[chunk.message_hash]
        chunked_message.set_result(chunk)
        if chunked_message.is_done:
            del self._messages_by_hash[chunk.message_hash]

        if received_first_chunk_of_new_message:
            return chunked_message


class ChunkedMessage:

    def __init__(self, total_number_of_chunks):
        self._chunk_futures = [asyncio.Future() for _ in
                               range(total_number_of_chunks)]

    @property
    async def full_payload(self):
        all_chunks = await asyncio.gather(*self._chunk_futures)
        return b''.join(chunk.data for chunk in all_chunks)

    @property
    async def chunks(self):
        for chunk_future in self._chunk_futures:
            yield (await chunk_future)

    def set_result(self, chunk):
        self._chunk_futures[chunk.chunk_index].set_result(chunk)

    @property
    def is_done(self):
        return all(future.done() for future in self._chunk_futures)


if __name__ == '__main__':
    def assert_equal(lhs, rhs):
        if lhs != rhs:
            raise AssertionError(f'{lhs} != {rhs}')

    teststring_a = b'the quick lazy frox jumps over the lazy dog'
    teststring_b = b'the quick lazy frox jumps over the lrazy duuuuug'

    async def new_chunk_generator():
        for teststring in [teststring_a, teststring_b]:
            for split in  Splitter(3, teststring).splits:
                await asyncio.sleep(0.001)
                yield split

    async def test():
        message_receiver = ChunkedMessageReceiver(new_chunk_generator())
        received_full_payloads = []
        async for message in message_receiver.received_messages:
            received_full_payloads.append(await message.full_payload)
        assert_equal(teststring_a, received_full_payloads[0])
        assert_equal(teststring_b, received_full_payloads[1])

    asyncio.get_event_loop().run_until_complete(test())
