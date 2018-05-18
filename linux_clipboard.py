import asyncio
import signal

from PyQt5.QtCore import QBuffer
from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import QIODevice
from PyQt5.QtCore import QMimeData

import log
from image import convert_to_png


logger = log.getLogger(__name__)


# TODO: rename this to QtClipboard? maybe it works with windows :P
class LinuxClipboard:

    @classmethod
    def new(cls, qt_app):
        return cls(qt_app.clipboard())

    def __init__(self, qt_clipboard):
        self._qt_clipboard = qt_clipboard

    async def update(self, clipboard_contents):
        convert_tif_to_png_to_fix_pasting_in_google_chrome_linux(clipboard_contents)
        qmimedata_to_set = QMimeDataSerializer.deserialize(clipboard_contents)
        self._qt_clipboard.setMimeData(qmimedata_to_set)

    def set_callback_for_updates(self, callback):
        def when_clipboard_changes():
            mime_data = self._qt_clipboard.mimeData()
            clipboard_contents = QMimeDataSerializer.serialize(mime_data)
            logger.debug(f'detected change {log.format_obj(clipboard_contents)}')
            if not self._contains_data(clipboard_contents):
                logger.debug('nothing to update, backing out')
                return
            asyncio.ensure_future(callback(clipboard_contents))
        self._qt_clipboard.dataChanged.connect(when_clipboard_changes)

    def _contains_data(self, clipboard_contents):
        return any(clipboard_contents.values())

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


# os x sends tiffs, pretty much always, and if we set a TIFF into the linux
# clipboard, it pretty much works! except google chrome can't paste it. and i
# need to paste into google chrome. so let's just do this conversion here. the
# cool thing is that PNGs seem to be smaller than TIFFs usually. hmmmmmm,
#
# TODO maybe i should just do this OS X side, because it shrinks the file size
# anyway, because of the lossless compression i suppose
def convert_tif_to_png_to_fix_pasting_in_google_chrome_linux(clipboard_contents):
    if 'image/tiff' in clipboard_contents:
        tiff_data = clipboard_contents.pop('image/tiff')
        clipboard_contents['image/png'] = convert_to_png(tiff_data)


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
