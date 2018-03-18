import functools


class ClipboardsCoordinator:

    def __init__(self):
        self._clipboards = []

    def add_clipboard(self, clipboard):
        # wrap the clipboard with ClipboardThatOnlyUpdatesOnChanges so we don't
        # update a clipboard if its value is already correct
        clipboard = ClipboardThatOnlyUpdatesOnChanges(clipboard)

        # each clipboard will callback `on_update` with the first argument as
        # itself whenever it receives an update
        callback = functools.partial(self.on_update, clipboard)
        clipboard.set_callback_for_updates(callback)
        self._clipboards.append(clipboard)

    async def on_update(self, changed_clipboard, contents):
        print('on update was called')
        print('all other clipboards: %r' %
              self._get_clipboards_other_than(changed_clipboard))
        for clipboard in self._get_clipboards_other_than(changed_clipboard):
            print('updating: %r' % clipboard)
            await clipboard.update(contents)

    def _get_clipboards_other_than(self, clipboard):
        return [c for c in self._clipboards if c is not clipboard]


class ClipboardThatOnlyUpdatesOnChanges:

    def __init__(self, clipboard):
        self._clipboard = clipboard
        self._checksum_of_clipboard = None

    async def update(self, clipboard_contents):
        checksum = generate_checksum(clipboard_contents)
        if checksum == self._checksum_of_clipboard:
            print('blocked a redundant update to %r' % self._clipboard)
            return

        await self._clipboard.update(clipboard_contents)
        self._checksum_of_clipboard = checksum

    def set_callback_for_updates(self, callback):
        async def update_cs_and_callback(msg):
            self._checksum_of_clipboard = generate_checksum(msg)
            await callback(msg)
        return self._clipboard.set_callback_for_updates(update_cs_and_callback)


def generate_checksum(clipboard_contents):
    return hash(str(clipboard_contents))
