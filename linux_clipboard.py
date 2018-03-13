import signal

from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import QBuffer
from PyQt5.QtCore import QIODevice
from PyQt5.QtWidgets import QApplication


class LinuxClipboard(object):

    @classmethod
    def new(cls):
        return cls(QApplication([]))

    def __init__(self, qt_app):
        self._qt_app = qt_app
        self._qt_clipboard = qt_app.clipboard()

    def update(self, clipboard_contents):
        qmimedata_to_set = QMimeDataSerializer.deserialize(
            clipboard_contents)
        self._qt_clipboard.setMimeData(qmimedata_to_set)

    def set_callback_for_updates(self, callback):
        def when_clipboard_changes():
            mime_data = self._qt_clipboard.mimeData()
            clipboard_contents = QMimeDataSerializer.serialize(mime_data)
            callback(clipboard_contents)
        self._qt_clipboard.dataChanged.connect(when_clipboard_changes)

    def poll_forever(self):
        self._fix_ctrl_c()
        return self._qt_app.exec_()

    # ctrl-c won't work without this: https://stackoverflow.com/a/5160720
    def _fix_ctrl_c(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)


class QMimeDataSerializer(object):

    @classmethod
    def serialize(cls, qmimedata):
        # the normal case
        if not qmimedata.hasImage():
            formats = qmimedata.formats()
            return {format: qmimedata.data(format).data() for format in formats}

        # we have to special case images because the same image is available in
        # many different formats. if we were to use them all, we would send
        # over the image several times instead of just once

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
    from PyQt5.QtWidgets import QApplication

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
