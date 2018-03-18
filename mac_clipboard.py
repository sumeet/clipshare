import asyncio
import time

from ScriptingBridge import NSArray
from ScriptingBridge import NSImage
from ScriptingBridge import NSPasteboard
from ScriptingBridge import NSString


CLIPBOARD_POLL_INTERVAL_SECONDS = 0.5


class MacClipboard:

    @classmethod
    def new(cls):
        # just use the default asyncio event loop
        return cls(asyncio.get_event_loop(), NSPasteboard.generalPasteboard())

    def __init__(self, event_loop, pasteboard):
        self._event_loop = event_loop
        self._pasteboard = pasteboard

    @property
    def event_loop(self):
        return self._event_loop

    async def update(self, clipboard_contents):
        object_to_set = self._get_clipboard_object_to_set(clipboard_contents)
        if not object_to_set:
            all_types = repr(clipboard_contents.keys())
            print('unsupported clipboard payload with types: %s' % all_types)
            print('not gonna do anything')
        self._pasteboard.clearContents()
        self._pasteboard.writeObjects_(NSArray.arrayWithObject_(object_to_set))
        self._pasteboard.release()

    # by default the callback doesn't do anything. it has to be set by the
    # coordinator. this should be overwritten by the caller
    _callback = lambda *args: None

    def set_callback_for_updates(self, callback):
        self._callback = callback
        asyncio.ensure_future(self.poll_forever(), loop=self._event_loop)

    async def poll_forever(self):
        poller = Poller(self._pasteboard)

        while True:
            clipboard_contents = poller.poll_for_new_clipboard_contents()
            if clipboard_contents:
                print('found clipboard contents, calling back')
                await self._callback(clipboard_contents)
            await asyncio.sleep(CLIPBOARD_POLL_INTERVAL_SECONDS)

    def _get_clipboard_object_to_set(self, clipboard_contents):
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


class Poller:

    def __init__(self, pasteboard):
        self._pasteboard = pasteboard
        self._change_count = self._get_change_count()

    def poll_for_new_clipboard_contents(self):
        new_change_count = self._get_change_count()
        if new_change_count != self._change_count:
            self._change_count = new_change_count
            return extract_clipboard_contents(self._pasteboard)

    def _get_change_count(self):
        return self._pasteboard.changeCount()


MIME_TYPE_BY_READABLE_TYPE = {'public.tiff': 'image/tiff',
                              'public.utf8-plain-text': 'text/plain'}

READABLE_TYPES = MIME_TYPE_BY_READABLE_TYPE.keys()

def extract_clipboard_contents(pasteboard):
    data_type = pasteboard.availableTypeFromArray_(READABLE_TYPES)
    mime_type = MIME_TYPE_BY_READABLE_TYPE.get(data_type)
    if not mime_type:
        return None
    clipboard_data = bytes(pasteboard.dataForType_(data_type))
    return {mime_type: clipboard_data}
