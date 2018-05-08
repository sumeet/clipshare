import asyncio
import signal

from PyQt5.QtCore import QBuffer
from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import QIODevice
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication
from quamash import QEventLoop

import log


logger = log.getLogger(__name__)


# TODO: rename this to QtClipboard?
class LinuxClipboard:

    # XXX: this interface seems a bit strange. we're creating a clipboard
    # object and right there we're also creating the event loop. it works for
    # now! but it might change
    @classmethod
    def new(cls):
        # lol, move this somewhere better
        # XXX: ugh i forgot what this is for
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        app = QApplication([])
        loop = QEventLoop(app)
        return cls(loop, app.clipboard())

    def __init__(self, event_loop, qt_clipboard):
        self._event_loop = event_loop
        self._qt_clipboard = qt_clipboard

    @property
    def event_loop(self):
        return self._event_loop

    async def update(self, clipboard_contents):
        qmimedata_to_set = QMimeDataSerializer.deserialize(
            clipboard_contents)
        self._qt_clipboard.setMimeData(qmimedata_to_set)

    def set_callback_for_updates(self, callback):
        def when_clipboard_changes():
            mime_data = self._qt_clipboard.mimeData()
            clipboard_contents = QMimeDataSerializer.serialize(mime_data)
            logger.debug(f'detected change {log.format_obj(clipboard_contents)}')
            if not clipboard_contents:
                logger.debug('nothing to update, backing out')
                return
            asyncio.ensure_future(callback(clipboard_contents),
                                  loop=self._event_loop)
        self._qt_clipboard.dataChanged.connect(when_clipboard_changes)

    def __repr__(self):
        return f'<{type(self).__name__}>'


class QMimeDataSerializer:

    WORKING_NON_IMAGE_FORMATS = set(['text/plain'])

    @classmethod
    def serialize(cls, qmimedata):
        if qmimedata.hasImage():
            # TODO: see if this can be something other than png. i think it'll suck
            # to send huge jpegs over the wire as png
            return {'image/png': cls._extract_image(qmimedata)}
        formats = qmimedata.formats()
        compatible_formats = cls.WORKING_NON_IMAGE_FORMATS.intersection(formats)
        return {format: qmimedata.data(format).data() for format in compatible_formats}

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
