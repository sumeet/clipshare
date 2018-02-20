import flask

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import requests
import threading

clipboard = ""


def refresh_osg(clipboard):
    response = requests.post("http://osg:31337/paste",
                             json={'text': clipboard})
    print(response)


def callBack(clip, event):
    global clipboard
    print("clipboard changed, retrieving text from clipboard")
    clipboard = clip.wait_for_text()
    print("clipboard says %r" % clipboard)
    refresh_osg(clipboard)


clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
def set_text(text):
    print('set text')
    clip.set_text(text, -1)
    # gotta do this so the process doesn't block here???
    print('wait for test')
    clip.wait_for_text()

    print('store')
    clip.store()


app = flask.Flask(__name__)
@app.route('/paste', methods=['POST'])
def handle_remote_paste():
    paste = flask.request.get_json()
    print(paste)
    set_text(paste['text'])
    return "OK"


def watch_clipboard_for_changes():
    clip.connect('owner-change',callBack)
    Gtk.main()


if __name__ == '__main__':
    t = threading.Thread(name='gtk', target=watch_clipboard_for_changes)
    t.start()

    app.run(host='0.0.0.0', port=31337, debug=True)
    #t.join()
