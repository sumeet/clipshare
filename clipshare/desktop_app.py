import asyncio
import contextlib
import signal
import sys

from async_generator import asynccontextmanager
from cached_property import cached_property
from quamash import QEventLoop
from PyQt5.QtWidgets import QApplication

from . import log
from . import signals
from .client import Client
from .client_relay_node import ClientRelayNode
from .local_clipboard import LocalClipboard
from .relay import Relay
from .server import Server
from .settings import AppSettings
from .ui import SettingsWindow
from .ui import UI


logger = log.getLogger(__name__)


def start_ui(qapp):
    ui = UI(qapp)
    signals.incoming_transfer.connect(ui.handle_incoming_transfer_progress)
    signals.outgoing_transfer.connect(ui.handle_outgoing_transfer_progress)

    signals.connection_established.connect(ui.handle_connection_established)
    signals.connection_connecting.connect(ui.handle_connection_connecting)
    signals.connection_disconnected.connect(ui.handle_connection_disconnected)
    ui.start()
    return ui


class DesktopApp:

    def __init__(self, local_clipboard, qapp):
        self._local_clipboard = local_clipboard
        self._qapp = qapp

        self._ui = start_ui(self._qapp)
        self._relay = Relay()
        self._client = None
        self._server = None

    def start(self, event_loop):
        if self._client_and_server_both_disabled_in_settings:
            asyncio.ensure_future(self._show_configuration_required_warning())

        with self._relay.with_node(self._local_clipboard_relay_node):
            AppSettings.on_change.connect(lambda *args: self._reload_settings())
            self._reload_settings()
            event_loop.run_forever()

    def _reload_settings(self):
        settings = AppSettings.get

        if ((not settings.is_server_enabled) or
            (self._different_server_requested_in_settings(settings))):
            self._stop_server_if_running()

        if settings.is_server_enabled and not self._server:
            self._server = Server(settings.server_listen_ip,
                                  settings.server_listen_port, self._relay)
            self._server.start()

        if ((not settings.is_client_enabled) or
            (self._client and self._client.ws_url != settings.client_ws_url)):
            self._stop_client_if_running()

        if settings.is_client_enabled and not self._client:
            self._client = Client(settings.client_ws_url, self._relay)
            self._client.connect()

    def _different_server_requested_in_settings(self, settings):
        return self._server and (
            self._server.bind_host != settings.server_listen_ip or
            self._server.port != settings.server_listen_port)

    def _stop_server_if_running(self):
        if self._server:
            self._server.stop()
            self._server = None

    def _stop_client_if_running(self):
        if self._client:
            self._client.disconnect()
            self._client = None

    # either the client or the server must be running for this proggy to do
    # anything. keep prompting the user to do something til they choose
    async def _show_configuration_required_warning(self):
        await self._ui.show_notice(
            'Clipshare must be configured to run in either client mode or '
            "server mode before it'll sync your clipboard.")
        await self._ui.show_settings_window()

    @property
    def _client_and_server_both_disabled_in_settings(self):
        settings = AppSettings.get
        return not (settings.is_server_enabled or settings.is_client_enabled)


    @cached_property
    def _local_clipboard_relay_node(self):
        return ClientRelayNode(self._local_clipboard)


if __name__ == '__main__':
    # hide dock icon if on mac
    if sys.platform == 'darwin':
        from AppKit import NSBundle
        info = NSBundle.mainBundle().infoDictionary()
        info['LSUIElement'] = '1'

    # we need this to make it so ^c will quit the program
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    qapp = QApplication([])
    # this keeps the event loop running forever, instead of the standard
    # behavior of quitting as soon as the last window is closed.
    qapp.setQuitOnLastWindowClosed(False)

    event_loop = QEventLoop(qapp)
    asyncio.set_event_loop(event_loop)

    local_clipboard = LocalClipboard.new(qapp)
    desktop_app = DesktopApp(local_clipboard, qapp)
    with event_loop:
        desktop_app.start(event_loop)
