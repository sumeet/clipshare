import pickle
from ScriptingBridge import NSPasteboard, NSImage, NSArray
import sys


READABLE_TYPES = ['public.tiff', 'public.utf8-plain-text']


pb = NSPasteboard.generalPasteboard()


def serialize_to_file():
    data_type = pb.availableTypeFromArray_(READABLE_TYPES)
    if not data_type == 'public.tiff':
        print('not a tiff, exiting')
        sys.exit(1)

    data = bytes(pb.dataForType_(data_type))
    with open('clipboard.pickle', 'wb') as f:
        pickle.dump({'image/tiff': data}, f)



def load_file_into_clipboard():
    data = None
    with open('clipboard.pickle', 'rb') as f:
        data = pickle.load(f)['image/tiff']
    image = NSImage.alloc().initWithData_(data)
    pb.clearContents()
    pb.writeObjects_(NSArray.arrayWithObject_(image))
    pb.release()


#serialize_to_file()
load_file_into_clipboard()



#data_type = pb.availableTypeFromArray_(READABLE_TYPES)
#data = pb.dataForType_(data_type)

#image = NSImage.alloc().initWithData_(
