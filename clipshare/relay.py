import asyncio
import contextlib
import functools

from . import log


logger = log.getLogger(__name__)


class Relay:

    def __init__(self):
        self._nodes = []

    @contextlib.contextmanager
    def with_node(self, node):
        try:
            self._add_node(node)
            yield
        finally:
            self._remove_node(node)

    def _add_node(self, node):
        do_relay = functools.partial(self._relay_message_from_node, node)
        async def do_relay(message):
            await self._relay_message_from_node(node, message)
        # TODO: make sure this weak=False doesn't cause a memory leak
        node.new_message_signal.connect(do_relay, weak=False)
        self._nodes.append(node)
        logger.debug(f'added a node. all nodes now: {self._nodes}')
        node.start_relaying_changes()

    def _remove_node(self, node):
        self._nodes = self._get_nodes_other_than(node)
        logger.debug(f'removed a node. all nodes now: {self._nodes}')

    async def _relay_message_from_node(self, node, message):
        other_nodes = self._get_nodes_other_than(node)
        logger.debug(f'received update from {repr(node)}: {log.format_obj(message)}')
        futures = [self._send_message_to_node(node, message) for node in other_nodes]
        await asyncio.gather(*futures)

    async def _send_message_to_node(self, node, message):
        logger.debug(f'sending update to {repr(node)}: {log.format_obj(message)}')
        await node.accept_relayed_message(message)
        logger.debug(f'done sending update to {repr(node)}')

    def _get_nodes_other_than(self, other_than_node):
        return [node for node in self._nodes if node != other_than_node]
