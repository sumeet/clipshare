import asyncore
import json
import socket


from coordinator import ClipboardsCoordinator


MAX_MSG_SIZE = 16384            # 16MB should cover most things


class RemoteClipboard(object):

    def __init__(self, client_handler):
        self._client_handler = client_handler

    def update(self, clipboard_contents):
        utf8_encoded_json = json.dumps(clipboard_contents) \
                                .encode('utf-8')
        self._client_handler.send(utf8_encoded_json + b'\r\n')

    def set_callback_for_updates(self, callback):
        def message_handler(msg):
            try:
                deserialized = json.loads(msg.rstrip(b'\r\n'))
            except json.JSONDecodeError:
                print("got a bad payload over the wire from %r: %r" %
                      (self, msg))
                print("doing nothing")
                return
            return callback(deserialized)

        self._client_handler.callback = message_handler


class ClientHandler(asyncore.dispatcher_with_send):

    # by default the callback doesn't do anything. it has to be set by the
    # coordinator. this should be overridden by the caller
    callback = lambda *args: None

    def handle_read(self):
        data = self.recv(MAX_MSG_SIZE)
        if data:
            self.callback(data)

    # there's a method `send()` which transfers a msg to the connected client


class ClipboardServer(asyncore.dispatcher):

    def __init__(self, coordinator):
        super().__init__()
        self._coordinator = coordinator

    def run(self, host, port):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if not pair:
            return

        sock, addr = pair
        print('Incoming connection from %s' % repr(addr))
        client_handler = ClientHandler(sock)
        remote_clipboard = RemoteClipboard(client_handler)
        self._coordinator.add_clipboard(remote_clipboard)


if __name__ == '__main__':
    coordinator = ClipboardsCoordinator()
    server = ClipboardServer(coordinator)
    server.run('0.0.0.0', 8392)
    asyncore.loop()
