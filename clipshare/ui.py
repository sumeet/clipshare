import asyncio
import os.path
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtWidgets import QSystemTrayIcon

from . import log


DIR_PATH = os.path.dirname(os.path.realpath(__file__))


logger = log.getLogger(__name__)


class UI:

    def __init__(self, qapp):
        self._tray = Tray(qapp)
        self._progress_window = ProgressWindow(qapp)

    def start(self):
        self._tray.start()

    # XXX: the connection signals don't have send any args, but for some reason
    # blinker sends a None that causes an ArgumentError unless we just accept
    # it
    def handle_connection_established(self, *args):
        self._tray.handle_connection_established()

    def handle_connection_connecting(self, *args):
        self._tray.handle_connection_connecting()

    def handle_connection_disconnected(self, *args):
        self._tray.handle_connection_disconnected()

    def handle_incoming_transfer_progress(self, progress):
        self._progress_window.handle_incoming_transfer_progress(progress)
        self._tray.handle_incoming_transfer_progress(progress)

    def handle_outgoing_transfer_progress(self, progress):
        self._progress_window.handle_outgoing_transfer_progress(progress)
        self._tray.handle_outgoing_transfer_progress(progress)


# XXX: pry move tray and progress window into separate files
class Tray:

    RESET_ACTIVITY_INDICATOR_AFTER_SECONDS = 30

    class nullobject:
        def __getattr__(self, name):
            return type(self)()

    # XXX: getting rid of the connection var here
    def __init__(self, qapp):
        self._qapp = qapp
        self._connection = self.nullobject()

        self._qsystem_tray_icon = QSystemTrayIcon()
        self._icons = Icons()
        self._scheduler = Scheduler()
        self.set_icon(self._icons.disconnected)
        self._rebuild_menu()

    def start(self):
        # on mac, left clicking on a tray icon will both "activate" it, and
        # open up the context menu. on other platforms, we'll allow you to
        # easily turn off syncing by just clicking the menu icon. on mac you'll
        # have to go into the context menu.
        if sys.platform != 'darwin':
            self._qsystem_tray_icon.activated.connect(self._tray_icon_clicked)
        self._qsystem_tray_icon.show()

    def handle_connection_established(self):
        self.set_icon(self._icons.connected)
        self._rebuild_menu()

    def handle_connection_connecting(self):
        self.set_icon(self._icons.connecting)
        self._rebuild_menu()

    def handle_connection_disconnected(self):
        self.set_icon(self._icons.disconnected)
        self._rebuild_menu()

    def handle_incoming_transfer_progress(self, transfer_progress):
        if transfer_progress.is_complete:
            self.set_icon(self._icons.recently_received_from_remote)
            self._schedule_activity_indicator_to_go_back_to_normal()
        else:
            self.set_icon(self._icons.downloading)

    def handle_outgoing_transfer_progress(self, transfer_progress):
        if transfer_progress.is_complete:
            self.set_icon(self._icons.recently_sent_to_remote)
            self._schedule_activity_indicator_to_go_back_to_normal()
        else:
            self.set_icon(self._icons.uploading)

    def set_icon(self, icon):
        self._qsystem_tray_icon.setIcon(icon)

    # changing of the connection state could cause some of the menu options to
    # change. for example, if we're connected, then we want to show the user an
    # option to pause, and the other way around. so we will want to rebuild
    # often
    def _rebuild_menu(self):
        menu = QMenu()
        self._add_pause_menu_action(menu)
        self._add_quit_menu_action(menu)
        self._qsystem_tray_icon.setContextMenu(menu)

    def _add_pause_menu_action(self, menu):
        if self._connection.is_active:

            paused_action = menu.addAction('Pause clipboard syncing')
            #paused_action.triggered.connect(self._connection.disconnect)
        else:
            paused_action = menu.addAction('Connect to remote clipboard')
            #paused_action.triggered.connect(self._connection.connect)

    def _add_quit_menu_action(self, menu):
        quit_action = menu.addAction('Quit')
        quit_action.triggered.connect(self._qapp.quit)

    def _schedule_activity_indicator_to_go_back_to_normal(self):
        self._scheduler.schedule_task(
            lambda: self.set_icon(self._icons.connected),
            timeout=self.RESET_ACTIVITY_INDICATOR_AFTER_SECONDS)

    def _tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_pause()

    def _toggle_pause(self):
        if self._connection.is_active:
            self._connection.disconnect()
        else:
            self._connection.connect()


class Scheduler:
    """Scheduler which schedules a task for the future. If you try to schedule
    something else, cancels the scheduled task if it's still pending.

    It's used for:

    Resets the tray icon back to `normal` if there hasn't been any clipboard
    activity for a while.

    Normally when you copy something to the clipboard, you paste it right away.
    If a couple of minutes pass, you've probably even forgotten the fact that
    you copied something to it.

    So after a couple of minutes pass, instead of indicating that we recently
    sent to or received from the remote clipboard, just reset back to the
    indicator-less icon.
    """

    def __init__(self):
        self._task = None

    def schedule_task(self, func, *, timeout):
        if self._task and not self._task.done():
            logger.debug("there's already a timer running, cancelling it")
            self._task.cancel()
        future = self._wait_then_execute_task(func, timeout)
        self._task = asyncio.ensure_future(future)

    async def _wait_then_execute_task(self, func, timeout):
        logger.debug(f'waiting {timeout} seconds before executing {func}')
        await asyncio.sleep(timeout)
        logger.debug(f'executing {func}')
        func()


class Icons:

    def __init__(self):
        self.disconnected = self._load('009-verification.png')
        self.connecting = self._load('010-logistics.png')
        self.connected = self._load('002-clipboard.png')
        self.recently_sent_to_remote = self._load('001-list.png')
        self.recently_received_from_remote = self._load('008-miscellaneous-4.png')
        self.uploading = self._load('003-miscellaneous.png')
        self.downloading = self._load('004-miscellaneous-1.png')

    def _load(self, filename):
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
                'Receiving from remote clipboard\u2026')

        if transfer_progress.is_complete:
            self._close_if_open(self._incoming_progress_dialog)
            self._incoming_progress_dialog = None
            return

        self._incoming_progress_dialog.setRange(0, transfer_progress.total)
        self._incoming_progress_dialog.setValue(transfer_progress.completed)

    def handle_outgoing_transfer_progress(self, transfer_progress):
        if not self._outgoing_progress_dialog:
            self._outgoing_progress_dialog = self._open_dialog('Sending to remote clipboard\u2026')

        if transfer_progress.is_complete:
            self._close_if_open(self._outgoing_progress_dialog)
            self._outgoing_progress_dialog = None
            return

        self._outgoing_progress_dialog.setRange(0, transfer_progress.total)
        self._outgoing_progress_dialog.setValue(transfer_progress.completed)

    def _open_dialog(self, progress_dialog_title):
        progress_dialog = QProgressDialog()
        progress_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        progress_dialog.setWindowTitle('Clipshare')
        # XXX: for some reason, mac is clipping off the very ends of the label.
        # let's throw in some space so the whole thing shows up
        progress_dialog.setLabelText('    ' + progress_dialog_title + '    ')
        progress_dialog.setWindowOpacity(0.95)
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
