import time
import flask

#import gi
#gi.require_version('Gtk', '3.0')
#from gi.repository import Gtk, Gdk

import requests
import multiprocessing
import threading

clipboard = ""

def refresh_osg(clipboard):
    response = requests.post("http://osg:31337/paste",
                             json={'text': clipboard})
    print(response)


LAST_OPERATION_TIME = 0

import functools
# lol this is trash:
#
# FIXME: this is a super jank way of making it so that copying
# something to the clipboard doesn't cause a chain reaction.
#
# try and figure out the CORRECT way of stopping an event from
# propagating
def has_a_5_second_lockdown_in_front_of_it(func):
    # turn off the trash
    return func

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

from Queue import Queue, Empty, Full

just_wrote_to_our_own_clipboard_q = Queue()

#def prevent_the_next_clipboard_change_event_from_causing_infinite_loop():
    #def lock_once_for_the_next_n_seconds(n):
        #print("we just wrote to the clipboard, so we're going to stop ourselves")
        #print("from processing our own write")
        #try:
            #just_wrote_to_our_own_clipboard_q.put(None, timeout=n)
            #print("hmm the put worked")
        #except Full:
            #print("timed out waiting for our own clipboard write event after %d sec" % n)
            #print("whatever. stop waiting. we're probably not gonna get that event")
    #t = threading.Thread(target=lock_once_for_the_next_n_seconds, args=(10,))
    #t.start()
from threading import Lock

just_wrote_to_our_own_clipboard_lock = Lock()
import time
def prevent_the_next_clipboard_change_event_from_causing_infinite_loop():
    def lock_it_for(n_seconds):
        is_locked = just_wrote_to_our_own_clipboard_lock.acquire(False)
        time.sleep(n_seconds)
        try:
            just_wrote_to_our_own_clipboard_lock.release()
        except:
            print("oh so the lock wasn't actually held, who cares")

    t = threading.Thread(target=lock_it_for, args=(10,))
    t.start()

#def did_we_just_write_to_our_own_clipboard():
    #try:
        #just_wrote_to_our_own_clipboard_q.get_nowait()
        #return True
    #except Empty:
        #return False

def did_we_just_write_to_our_own_clipboard():
     got_lock = just_wrote_to_our_own_clipboard_lock.acquire(False)
     try:
         just_wrote_to_our_own_clipboard_lock.release()
     except:
        print("oh so the lock wasn't actually held, who cares")
     # if we got the lock, then something isn't holding it, meaning we dind't
     # just write to the clipboard
     if got_lock:
         return False
     else:
         return True


@has_a_5_second_lockdown_in_front_of_it
def callBack(clip, event):
    print("XXXX callBack is getting called: %r" % event)

    global clipboard
    print("clipboard changed, retrieving text from clipboard")
    clipboard = clip.wait_for_text()
    print("clipboard says %r" % clipboard)

    if not did_we_just_write_to_our_own_clipboard():
        print("refreshing osg bc we didn't just write to our own clipboard")
        refresh_osg(clipboard)
    else:
        print("preventing write to osg")



def get_clipboard():
    # import pygtk here so that each process imports their own
    # pygtk lazily when they need it. we want it to be imported
    # twice
    import pygtk
    pygtk.require('2.0')
    import gtk
    return gtk.clipboard_get()


@has_a_5_second_lockdown_in_front_of_it
def set_text(text):
    #clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clip = get_clipboard()

    prevent_the_next_clipboard_change_event_from_causing_infinite_loop()

    print('XXXX setting the clipboard')
    clip.set_text(text)


    prevent_the_next_clipboard_change_event_from_causing_infinite_loop()

    print('store')
    clip.store()



app = flask.Flask(__name__)
@app.route('/paste', methods=['POST'])
def handle_remote_paste():
    paste = flask.request.get_json()
    print('incoming request: %r' % paste)
    set_text(paste['text'])
    return "OK"


def watch_clipboard_for_changes():
    import gtk
    clip = get_clipboard()

    while True:
        try:
            clip.connect('owner-change',callBack)
            gtk.main()
            #Gtk.main()
        except Exception as e:
            print("gtk died: %r, restarting" % e)


def flask_app():
    app.run(host='0.0.0.0', port=31337, debug=True)

if __name__ == '__main__':
    t = multiprocessing.Process(
            target=watch_clipboard_for_changes)
    t.start()
    #watch_clipboard_for_changes()
    #t.join()
    flask_app()
