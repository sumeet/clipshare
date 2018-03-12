from ScriptingBridge import NSArray
from ScriptingBridge import NSImage
from ScriptingBridge import NSPasteboard
from ScriptingBridge import NSString


READABLE_TYPES = ['public.tiff', 'public.utf8-plain-text']


class MacClipboard(object):

    @classmethod
    def new(cls):
        return cls(NSPasteboard.generalPasteboard())

    def __init__(self, pasteboard):
        self._pasteboard = pasteboard

    def update(self, clipboard_contents):
        object_to_set = self._get_clipboard_object_to_set(clipboard_contents)
        if not object_to_set:
            all_types = repr(clipboard_contents.keys())
            print('unsupported clipboard payload with types: %s' % all_types)
            print('not gonna do anything')
        self._pasteboard.clearContents()
        self._pasteboard.writeObjects_(NSArray.arrayWithObject_(object_to_set))
        self._pasteboard.release()

    def set_callback_for_updates(self, callback):
        # TODO: get this working later
        return

    def poll_forever(self):
        import time
        print('sleeping 4evre')
        time.sleep(99999)

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
