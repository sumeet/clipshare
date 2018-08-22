import asyncio
import contextlib
import signal
import sys

from cached_property import cached_property
from quamash import QEventLoop
from PyQt5.QtWidgets import QApplication

from . import log
from . import signals
from .client import Connection
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
        self._relay = Relay()

    async def start(self):
        ui = start_ui(self._qapp)

        # either the client or the server must be running for this proggy to do
        # anything. keep prompting the user to do something til they choose
        while self._client_and_server_both_disabled_in_settings:
            ui.show_notice(
                'Clipshare must be configured to run in either client mode or '
                "server mode before it'll sync your clipboard.")
            SettingsWindow().show()

        with self._relay.with_node(self._local_clipboard_relay_node):
            if settings.is_server_enabled:
                server = Server(self._relay)
                asyncio.ensure_future(server.serve(settings.server_listen_ip,
                                                   settings.server_listen_port))


            #yield

            # TODO: when i code this, just disconnect the client on every save.
            #
            # it doesn't matter if the client disconnects every time we save,
            # it shouldn't cause an interruption anyway.
            if settings.is_client_enabled:
                connection = Connection(self._relay, settings.client_ws_url)
                ## XXX: we've gotta open the connection AFTER starting the UI, or else
                ## the UI will be in a bad state.
                connection.connect()

            #nix this timer stuff, see if i can manage to do in a way where we
            # don't have to poll
            while True:
                await asyncio.sleep(1.5)

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
    event_loop = QEventLoop(qapp)
    asyncio.set_event_loop(event_loop)
    local_clipboard = LocalClipboard.new(qapp)

    desktop_app = DesktopApp(local_clipboard, qapp)
    with event_loop:
        asyncio.ensure_future(desktop_app.start())
        event_loop.run_forever()
        logger.debug('exited the event loop')
