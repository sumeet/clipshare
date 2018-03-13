import asyncore
import pickle as json
import socket
import struct
import sys
import threading

from local_clipboard import LocalClipboard
from coordinator import ClipboardsCoordinator


class RemoteClipboard(object):

    def __init__(self, client_handler):
        self._client_handler = client_handler

    def update(self, clipboard_contents):
        output = json.dumps(clipboard_contents)
        self._client_handler.send(output + b'\r\n')

    def set_callback_for_updates(self, callback):
        def message_handler(msg):
            try:
                deserialized = json.loads(msg.rstrip(b'\r\n'))
            except:
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
        data = self._recv_msg()
        if data:
            self.callback(data)

    def send(self, msg):
        # Prefix each message with a 4-byte length (network byte order)
        print('sending len is')
        print(len(msg))
        msg = struct.pack('>I', len(msg)) + msg
        super().send(msg)

    def _recv_msg(self):
        # Read message length and unpack it into an integer
        raw_msglen = self._recvall(4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        print('recv len is')
        print(msglen)
        # Read the message data
        return self._recvall(msglen)

    def _recvall(self, n):
        # Helper function to recv n bytes or return None if EOF is hit
        data = b''
        while len(data) < n:
            print("an iteration")
            packet = self.recv(n - len(data))
            if not packet:
                continue
            data += packet
        return data

    def recv(self, buffer_size):
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                # a closed connection is indicated by signaling
                # a read condition, and having recv() return 0.
                self.handle_close()
                return b''
            else:
                return data
        except socket.error as why:
            if why.args[0] in (socket.EAGAIN, socket.EWOULDBLOCK):
                return b''
            else:
                raise


class ClipboardClient(asyncore.dispatcher):

    def __init__(self, coordinator):
        super().__init__()
        self._coordinator = coordinator

    def run(self, host, port):
        self.create_socket()
        self.connect((host, port))

        sock = self.socket
        client_handler = ClientHandler(sock)
        remote_clipboard = RemoteClipboard(client_handler)
        self._coordinator.add_clipboard(remote_clipboard)


if __name__ == '__main__':
    local_clipboard = LocalClipboard.new()
    coordinator = ClipboardsCoordinator()
    coordinator.add_clipboard(local_clipboard)

    client = ClipboardClient(coordinator)
    client.run('somt.hopto.org', 8392)

    async_event_loop_thread = threading.Thread(target=asyncore.loop)
    async_event_loop_thread.start()

    local_clipboard.poll_forever()
