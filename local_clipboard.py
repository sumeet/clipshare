from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication

class LocalClipboard(object):

    @classmethod
    def new(cls):
        return cls(QApplication([]))

    def __init__(self, qt_clipboard):
        self._qt_clipboard = qt_clipboard

    def update(self, clipboard_contents):
        qmimedata_to_set = qmimedata.deserialize(clipboard_contents)
        self._qt_clipboard.setMimeData(qmimedata_to_set)

    def set_callback_for_updates(self, callback):
        # as of now the server can only send us one kind of message
        def on_clip_owner_change(clip, event):
            # FIXME: this is hardcoded to text
            clipboard_contents = clip.wait_for_text()
            callback(clipboard_contents)

        #self._qt_clipboard.connect('owner-change', on_clip_owner_change)
        # TODO: start the gtk loop in a thread
        # TODO: have to configure Gtk for threading correctly using the link
        #       shivaram gave me
        # Gtk.main()


class QMimeDataSerializer(object):

    @classmethod
    def serialize(cls, qmimedata):
        formats = qmimedata.formats()
        return {format: qmimedata.data(format).data() for format in formats}

    @classmethod
    def deserialize(cls, serialized):
        qmimedata = QMimeData()
        for format, data in serialized.items():
            qmimedata.setData(format, data)
        return qmimedata


if __name__ == '__main__':
    app = QApplication([])
    clipboard = app.clipboard()
    md = clipboard.mimeData()

    print("serialized:")
    serialized = QMimeDataSerializer.serialize(md)
    print(serialized)
    print("deserialized:")
    deserialized = QMimeDataSerializer.deserialize(serialized)
    reserialized = QMimeDataSerializer.serialize(deserialized)
    print(reserialized)

    assert serialized == reserialized
