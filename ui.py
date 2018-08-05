import asyncio
import os.path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtWidgets import QSystemTrayIcon

import log


DIR_PATH = os.path.dirname(os.path.realpath(__file__))


logger = log.getLogger(__name__)


class UI:

    def __init__(self, qapp):
        self._qapp = qapp
        self._tray = Tray()
        self._progress_window = ProgressWindow(qapp)

    def start(self):
        self._tray.show()

    def handle_incoming_transfer_progress(self, progress):
        self._progress_window.handle_incoming_transfer_progress(progress)
        self._tray.handle_incoming_transfer_progress(progress)

    def handle_outgoing_transfer_progress(self, progress):
        self._progress_window.handle_outgoing_transfer_progress(progress)
        self._tray.handle_outgoing_transfer_progress(progress)


# XXX: pry move tray and progress window into separate files
class Tray:

    def __init__(self):
        self._qsystem_tray_icon = QSystemTrayIcon()
        self._icons = Icons()
        self._reset_tray_timer = ResetTrayTimer(self)
        self.set_icon_to_normal()

    def handle_incoming_transfer_progress(self, transfer_progress):
        if transfer_progress.is_complete:
            self._set_icon(self._icons.recently_received_from_remote)
            self._reset_tray_timer.start_timer_to_reset_tray_back_to_normal()
        else:
            self._set_icon(self._icons.downloading)

    def handle_outgoing_transfer_progress(self, transfer_progress):
        if transfer_progress.is_complete:
            self._set_icon(self._icons.recently_sent_to_remote)
            self._reset_tray_timer.start_timer_to_reset_tray_back_to_normal()
        else:
            self._set_icon(self._icons.uploading)

    def set_icon_to_normal(self):
        self._set_icon(self._icons.normal)

    def show(self):
        self._qsystem_tray_icon.show()

    def _set_icon(self, icon):
        self._qsystem_tray_icon.setIcon(icon)


class ResetTrayTimer:
    """Resets the tray icon back to `normal` if there hasn't been any clipboard
    activity for a while.

    Normally when you copy something to the clipboard, you paste it right away.
    If a couple of minutes pass, you've probably even forgotten the fact that
    you copied something to it.

    So after a couple of minutes pass, instead of indicating that we recently
    sent to or received from the remote clipboard, just reset back to the
    indicator-less icon.
    """

    RESET_IN_SECONDS = 30

    def __init__(self, tray):
        self._tray = tray
        self._task = None

    def start_timer_to_reset_tray_back_to_normal(self):
        if self._task and not self._task.done():
            logger.debug("there's already a timer running, cancelling it")
            self._task.cancel()
        self._task = asyncio.ensure_future(
            self._wait_then_set_tray_back_to_normal())


    async def _wait_then_set_tray_back_to_normal(self):
        logger.debug('starting timer to reset tray back to normal')
        await asyncio.sleep(self.RESET_IN_SECONDS)
        logger.debug('done waiting on timer, resetting tray icon')
        self._tray.set_icon_to_normal()


class Icons:

    def __init__(self):
        self.normal = self._icon('002-clipboard.png')
        self.recently_sent_to_remote = self._icon('001-list.png')
        self.recently_received_from_remote = self._icon('008-miscellaneous-4.png')
        self.uploading = self._icon('003-miscellaneous.png')
        self.downloading = self._icon('004-miscellaneous-1.png')

    def _icon(self, filename):
        # XXX: for some reason, QIcon doesn't crash if the file doesn't exist.
        path_to_icon = os.path.join(DIR_PATH, 'coloredicons', 'png', filename)
        if not os.path.exists(path_to_icon):
            raise Exception(f"fatal error: {path_to_icon} doesn't exist")
        return QIcon(path_to_icon)


class ProgressWindow:

    def __init__(self, qapp):
        self._qapp = qapp
        self._incoming_progress_dialog = None
        self._outgoing_progress_dialog = None

    def handle_incoming_transfer_progress(self, transfer_progress):
        if not self._incoming_progress_dialog:
            self._incoming_progress_dialog = self._open_dialog(
                "Receiving from remote clipboard\u2026")

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
