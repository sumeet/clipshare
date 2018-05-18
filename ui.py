from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtGui import QCursor

import log


logger = log.getLogger(__name__)


class UI:

    def __init__(self, qapp):
        self._qapp = qapp
        self._incoming_progress_dialog = None
        self._outgoing_progress_dialog = None

    def handle_incoming_transfer_progress(self, transfer_progress):
        if not self._incoming_progress_dialog:
            self._incoming_progress_dialog = self._open_dialog("Receiving from remote clipboard\u2026")

        if transfer_progress.is_complete:
            self._close_if_open(self._incoming_progress_dialog)
            self._incoming_progress_dialog = None
            return

        self._incoming_progress_dialog.setRange(0, transfer_progress.total)
        self._incoming_progress_dialog.setValue(transfer_progress.completed)

    def handle_outgoing_transfer_progress(self, transfer_progress):
        if not self._outgoing_progress_dialog:
            self._outgoing_progress_dialog = self._open_dialog("Sending to remote clipboard\u2026")

        if transfer_progress.is_complete:
            self._close_if_open(self._outgoing_progress_dialog)
            self._outgoing_progress_dialog = None
            return

        self._outgoing_progress_dialog.setRange(0, transfer_progress.total)
        self._outgoing_progress_dialog.setValue(transfer_progress.completed)

    def _open_dialog(self, progress_dialog_title):
        progress_dialog = QProgressDialog()
        progress_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        progress_dialog.setWindowTitle("Clipshare")
        progress_dialog.setLabelText(progress_dialog_title)
        progress_dialog.setWindowOpacity(0.75)
        progress_dialog.canceled.connect(progress_dialog.hide)
        progress_dialog.move(get_cursor_position(self._qapp))
        progress_dialog.show()
        return progress_dialog

    def _close_if_open(self, progress_dialog):
        if progress_dialog:
            progress_dialog.hide()


# https://stackoverflow.com/questions/32040202/
def get_cursor_position(qapp):
    global_cursor_pos = QCursor.pos()
    mouse_screen = qapp.desktop().screenNumber(global_cursor_pos)
    mouse_screen_geometry = qapp.desktop().screen(mouse_screen).geometry()
    return global_cursor_pos - mouse_screen_geometry.topLeft()
