from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import QBuffer
from PyQt5.QtCore import QIODevice
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
        # the normal case
        if not qmimedata.hasImage():
            formats = qmimedata.formats()
            return {format: qmimedata.data(format).data() for format in formats}

        # we have to special case images for two reasons:
        # (1) the above serialization doesn't work on mac
        # (2) on linux, the same image is available in many different formats.
        #     if we were to use them all, we would send over the image several
        #     times instead of just once

        # TODO: see if this can be something other than png. i think it'll suck
        # to send huge jpegs over the wire as png
        return {'image/png': cls._extract_image(qmimedata)}

    @classmethod
    def deserialize(cls, serialized):
        qmimedata = QMimeData()
        for format, data in serialized.items():
            qmimedata.setData(format, data)
        return qmimedata

    @classmethod
    def _extract_image(cls, qmimedata):
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.WriteOnly)
        qmimedata.imageData().save(buffer, 'PNG')
        return ba.data()


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
