import pickle           # lol it works


class RemoteClipboard(object):

    def __init__(self, sock):
        self._sock = sock

    async def update(self, clipboard_contents):
        output = pickle.dumps(clipboard_contents)
        await self._sock.send_message(output)

    def set_callback_for_updates(self, callback):
        def message_handler(msg):
            try:
                deserialized = pickle.loads(msg)
            except:
                print("got a bad payload over the wire from %r: %r" %
                      (self, msg))
                print("doing nothing")
                return
            return callback(deserialized)

        self._sock.callback = message_handler
