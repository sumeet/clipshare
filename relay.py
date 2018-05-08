import contextlib
import functools

import log


logger = log.getLogger(__name__)


class Relay:

    def __init__(self):
        self._clipboards = []

    @contextlib.contextmanager
    def with_clipboard(self, clipboard):
        try:
            self.add_clipboard(clipboard)
            yield
        finally:
            self.remove_clipboard(clipboard)

    def add_clipboard(self, clipboard):
        # wrap the clipboard with ClipboardThatOnlyUpdatesOnChanges so we don't
        # update a clipboard if its value is already correct
        clipboard = ClipboardThatOnlyUpdatesOnChanges(clipboard)

        # each clipboard will callback `on_update` with the first argument as
        # itself whenever it receives an update
        callback = functools.partial(self.on_update, clipboard)
        clipboard.set_callback_for_updates(callback)

        self._clipboards.append(clipboard)
        logger.debug(f'added a clipboard. all clipboards now: {self._clipboards}')

    def remove_clipboard(self, clipboard):
        self._clipboards = self._get_clipboards_other_than(clipboard)
        logger.debug(f'removed a clipboard. all clipboards now: {self._clipboards}')

    async def on_update(self, changed_clipboard, contents):
        all_other_clipboards = self._get_clipboards_other_than(changed_clipboard)
        for clipboard in all_other_clipboards:
            logger.debug(f'sending update to {repr(clipboard)} {log.format_obj(contents)}')
            await clipboard.update(contents)

    def _get_clipboards_other_than(self, clipboard):
        return [c for c in self._clipboards if c != clipboard]


class ClipboardThatOnlyUpdatesOnChanges:

    def __init__(self, clipboard):
        self._clipboard = clipboard
        self._checksum_of_clipboard = None

    async def update(self, clipboard_contents):
        checksum = generate_checksum(clipboard_contents)
        if checksum == self._checksum_of_clipboard:
            logger.debug(f'blocked a redundant update to {repr(self)} {log.format_obj(clipboard_contents)}')
            return

        await self._clipboard.update(clipboard_contents)
        self._checksum_of_clipboard = checksum

    def set_callback_for_updates(self, callback):
        async def update_cs_and_callback(msg):
            self._checksum_of_clipboard = generate_checksum(msg)
            await callback(msg)
        return self._clipboard.set_callback_for_updates(update_cs_and_callback)

    def __eq__(self, other):
        return self is other or self._clipboard is other

    # this is the clipboard that ends up getting logged, so let's just stick
    # the logging code in here
    def __repr__(self):
        return repr(self._clipboard)


def generate_checksum(clipboard_contents):
    return hash(str(clipboard_contents))
