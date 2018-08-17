import contextlib

from asyncblink import AsyncSignal
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
        self.new_clipboard_contents_signal = AsyncSignal()
        self._qt_clipboard = qt_clipboard

    def set(self, clipboard_contents):
        with self._stop_receiving_clipboard_updates():
            convert_tif_to_png_to_fix_pasting_in_google_chrome_linux(clipboard_contents)
            qmimedata_to_set = QMimeDataSerializer.deserialize(clipboard_contents)
            self._qt_clipboard.setMimeData(qmimedata_to_set)

    def clear(self):
        with self._stop_receiving_clipboard_updates():
            self._qt_clipboard.clear()

    def start_listening_for_changes(self):
        self._qt_clipboard.dataChanged.connect(self._grab_and_signal_clipboard_data)

    # temporarily stop listening to the clipboard while we set it, because we
    # don't want to detect our own updates
    @contextlib.contextmanager
    def _stop_receiving_clipboard_updates(self):
        try:
            self._qt_clipboard.dataChanged.disconnect(self._grab_and_signal_clipboard_data)
            yield
        finally:
            self.start_listening_for_changes()

    def _grab_and_signal_clipboard_data(self):
        mime_data = self._qt_clipboard.mimeData()
        clipboard_contents = QMimeDataSerializer.serialize(mime_data)
        logger.debug(f'detected change {log.format_obj(clipboard_contents)}')
        if self._contains_data(clipboard_contents):
            self.new_clipboard_contents_signal.send(clipboard_contents)
        else:
            logger.debug('nothing to update, backing out')

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
        image_data = qmimedata.imageData()
        if not image_data:
            raise ClipboardHadNoImageError(qmimedata)
        image_data.save(buffer, 'PNG')
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


class ClipboardHadNoImageError(Exception):

    def __init__(self, qmimedata):
        self._qmimedata = qmimedata

    def __str__(self):
        return ("Couldn't find an image in the clipboard contents: "
                f'{self._format_clipboard_contents}')

    @property
    def _format_clipboard_contents(self):
        return {self._qmimedata.data(format).data() for format in
                self._qmimedata.formats()}


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
