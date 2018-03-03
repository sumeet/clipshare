from collections import namedtuple
import functools


class ClipboardsCoordinator(object):

    def __init__(self, clipboards):
        self._clipboards = clipboards

    def start_coordinating(self):
        for cb in self._clipboards:
            # each clipboard will callback `on_update` with the first argument
            # as itself whenever it receives an update
            callback = functools.partial(self.on_update, cb)
            cb.on_updates_call(callback)

    def on_update(self, changed_clipboard, contents):
        for cb in self._get_clipboards_other_than(changed_clipboard):
            cb.update_if_changed(contents)

    def _get_clipboards_other_than(self, clipboard):
        return [c for c in self._clipboards if c != clipboard]


class ServerClipboard(object):

    def __init__(self, connection):
        self._connection = connection

    def update(self, clipboard_contents):
        self._connection.send(self._serialize(clipboard_contents))

    def on_updates_call(self, callback):
        # as of now the server can only send us one kind of message
        def incoming_msg_handler(msg):
            clipboard_contents = self._deserialize(msg)
            callback(clipboard_contents)
        self._connection.set_incoming_msg_handler(incoming_msg_handler)

    # it's just text for now
    def _serialize(self, clipboard_contents):
        return clipboard_contents.text

    def _deserialize(self, text):
        return ClipboardContents(text)


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class LocalClipboard(object):

    def __init__(self, gtk_clipboard):
        self._gtk_clipboard = gtk_clipboard

    def update(self, clipboard_contents):
        self._gtk_clipboard.set_text(clipboard_contents.text)
        self._gtk_clipboard.store()

    def on_updates_call(self, callback):
        # as of now the server can only send us one kind of message
        def on_clip_owner_change(clip, event):
            # FIXME: this is hardcoded to text
            clipboard_contents = clip.wait_for_text()
            callback(clipboard_contents)

        self._gtk_clipboard.connect('owner-change', on_clip_owner_change)
        # TODO: start the gtk loop in a thread
        # TODO: have to configure Gtk for threading correctly using the link
        #       shivaram gave me
        # Gtk.main()



class ClipboardThatOnlyUpdatesOnChanges(object):

    def __init__(self, clipboard):
        self._clipboard = clipboard
        self._checksum_of_clipboard = None

    def update(self, clipboard_contents_to_update):
        checksum = generate_checksum(clipboard_contents_to_update)
        if checksum == self._checksum_of_clipboard:
            return

        self._clipboard.update(clipboard_contents)
        self._checksum_of_clipboard = checksum

    def on_updates_call(self, *args, **kwargs):
        return self._clipboard.on_updates_call(*args, **kwargs)

def generate_checksum(clipboard_contents):
    return hash(clipboard_contents)


# just text for now
ClipboardContents = namedtuple('ClipboardContents', 'text')
