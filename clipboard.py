from collections import namedtuple
import functools
import pickle as json


class ServerClipboard(object):

    def __init__(self, connection):
        self._connection = connection

    def update(self, clipboard_contents):
        self._connection.send(json.dumps(clipboard_contents))

    def set_callback_for_updates(self, callback):
        # as of now the server can only send us one kind of message
        def incoming_msg_handler(msg):
            callback(json.loads(msg))
        self._connection.set_incoming_msg_handler(incoming_msg_handler)


