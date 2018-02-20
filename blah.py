import time
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


LAST_OPERATION_TIME = 0

import functools
def has_a_5_second_lockdown_in_front_of_it(func):
    @functools.wraps(func)
    def newfunc(*args, **kwargs):
        global LAST_OPERATION_TIME

        print("starting context manager")
        if time.time() - LAST_OPERATION_TIME <= 5:
            print("did something pretty recently, so bailing")
            return

        try:
            LAST_OPERATION_TIME = time.time()
            print("running the body")
            func(*args, **kwargs)
        finally:
            print("setting the time")
            LAST_OPERATION_TIME = time.time()
    
    return newfunc



@has_a_5_second_lockdown_in_front_of_it
def callBack(clip, event):
    global clipboard
    print("clipboard changed, retrieving text from clipboard")
    clipboard = clip.wait_for_text()
    print("clipboard says %r" % clipboard)
    refresh_osg(clipboard)


@has_a_5_second_lockdown_in_front_of_it
def set_text(text):
    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)


    print('set text')
    clip.set_text(text, -1)

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
    set_text("testing this bullassshit")
    time.sleep(1)
    exit(0)
    #t = threading.Thread(name='gtk', target=watch_clipboard_for_changes)
    #t.start()

    app.run(host='0.0.0.0', port=31337, debug=True)
    #t.join()
