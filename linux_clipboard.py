import asyncio
import signal

from PyQt5.QtCore import QBuffer
from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import QIODevice
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication
from quamash import QEventLoop


# TODO: rename this to QtClipboard?
class LinuxClipboard:

    # XXX: this interface seems a bit strange. we're creating a clipboard
    # object and right there we're also creating the event loop. it works for
    # now! but it might change
    @classmethod
    def new(cls):
        # lol, move this somewhere better
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
            print("linux clipboard changed, updating")
            asyncio.ensure_future(callback(clipboard_contents),
                                  loop=self._event_loop)
            # TODO: i just copy and pasted the above from stack overflow. why
            # do i need to do the above, and why can't i just do the below?
            #await callback(clipboard_contents)
        self._qt_clipboard.dataChanged.connect(when_clipboard_changes)

    # TODO: remove this method
    async def poll_forever(self):
        self._fix_ctrl_c()
        print("running the qt loop")
        return await self._qt_app.exec_()

    # ctrl-c won't work without this: https://stackoverflow.com/a/5160720
    def _fix_ctrl_c(self):
        # maybe we don't need to do this anymore
        pass
        #signal.signal(signal.SIGINT, signal.SIG_DFL)


class QMimeDataSerializer:

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
