import asyncio
import log
import time

from ScriptingBridge import NSArray
from ScriptingBridge import NSImage
from ScriptingBridge import NSPasteboard
from ScriptingBridge import NSString


logger = log.getLogger(__name__)


CLIPBOARD_POLL_INTERVAL_SECONDS = 0.5


class MacClipboard:

    @classmethod
    def new(cls, qt_app):
        # we don't use qt to read for the mac clipboard, for now
        return cls(NSPasteboard.generalPasteboard())

    def __init__(self, ns_pasteboard):
        self._ns_pasteboard = ns_pasteboard
        self._poller = Poller(self._ns_pasteboard)

    async def update(self, clipboard_contents):
        object_to_set = self._extract_settable_nsobject(clipboard_contents)
        if not object_to_set:
            all_types = repr(clipboard_contents.keys())
            logger.debug('unsupported clipboard payload ' +
                         log.format_obj(clipboard_contents))

        try:
            # pause the poller while we write to it, so we don't detect our own
            # changes
            self._poller.pause_polling()

            # for some reason you've gotta clear before writing or the write doesn't
            # have any effect
            self._ns_pasteboard.clearContents()
            self._ns_pasteboard.writeObjects_(
                NSArray.arrayWithObject_(object_to_set))

            # tell the poller to ignore the change we just made,
            self._poller.ignore_change_count(self._poller.current_change_count)
        finally:
            # and then when it resumes, it won't detect that change
            self._poller.resume_polling()

    # by default the callback doesn't do anything. it has to be set by the
    # relay. this should be overwritten by the caller
    _callback = lambda *args: None

    def set_callback_for_updates(self, callback):
        self._callback = callback
        asyncio.ensure_future(self.poll_forever())

    async def poll_forever(self):
        while True:
            clipboard_contents = self._poller.poll_for_new_clipboard_contents()
            if clipboard_contents:
                logger.debug(f'detected change {self._poller.current_change_count} '
                             + log.format_obj(clipboard_contents))
                await self._callback(clipboard_contents)

            await asyncio.sleep(CLIPBOARD_POLL_INTERVAL_SECONDS)

    def _extract_settable_nsobject(self, clipboard_contents):
        image_type = self._find_image_type(clipboard_contents)
        if image_type:
            image_data = clipboard_contents[image_type]
            return NSImage.alloc().initWithData_(image_data)
        elif 'text/plain' in clipboard_contents:
            bytes = clipboard_contents['text/plain']
            return NSString.alloc().initWithUTF8String_(bytes)
        # TODO: rich text, if i ever feel like i need it
        else:
            return None

    def _find_image_type(self, clipboard_contents):
        image_types = (t for t in clipboard_contents if t.startswith('image'))
        return next(image_types, None)

    def __repr__(self):
        return f'<{type(self).__name__}>'


class Poller:

    def __init__(self, ns_pasteboard):
        self._ns_pasteboard = ns_pasteboard
        self._last_seen_change_count = self.current_change_count
        self._paused = False
        self._change_count_to_ignore = None

    @property
    def current_change_count(self):
        return self._ns_pasteboard.changeCount()

    def poll_for_new_clipboard_contents(self):
        if self._paused:
            return None

        current_change_count = self.current_change_count
        # if the change count hasn't changed, the clipboard contents haven't
        # changed
        if current_change_count == self._last_seen_change_count:
            return None

        self._last_seen_change_count = current_change_count

        # this logic prevents us from propagating our own clipboard updates.
        # immediately after setting the clipboard, we tell ourselves to ignore that
        # update
        if current_change_count == self._change_count_to_ignore:
            logger.debug('ignoring bc we told ourselves to ignore '
                         f'{current_change_count}')
            return None

        return extract_clipboard_contents(self._ns_pasteboard)

    def pause_polling(self):
        self._paused = True

    def resume_polling(self):
        self._paused = False

    def ignore_change_count(self, change_count_to_ignore):
        self._change_count_to_ignore = change_count_to_ignore


MIME_TYPE_BY_READABLE_TYPE = {'public.tiff': 'image/tiff',
                              'public.utf8-plain-text': 'text/plain'}

READABLE_TYPES = MIME_TYPE_BY_READABLE_TYPE.keys()

def extract_clipboard_contents(ns_pasteboard):
    data_type = ns_pasteboard.availableTypeFromArray_(READABLE_TYPES)
    mime_type = MIME_TYPE_BY_READABLE_TYPE.get(data_type)
    if not mime_type:
        return None
    clipboard_data = bytes(ns_pasteboard.dataForType_(data_type))
    return {mime_type: clipboard_data}
