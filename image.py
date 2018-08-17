from io import BytesIO
from PIL import Image

import log


logger = log.get_logger(__name__)


# os x sends tiffs, and if we set a TIFF into the linux clipboard, it pretty
# much works. except google chrome can't paste it. and i need to paste into
# google chrome. so let's just do this conversion here. the cool thing is that
# PNGs seem to be way smaller than TIFFs, so we'll just do the same conversion
# on the os x side
def change_tiff_to_png(clipboard_contents):
    if clipboard_contents and 'image/tiff' in clipboard_contents:
        tiff_data = clipboard_contents.pop('image/tiff')
        clipboard_contents['image/png'] = convert_to_png(tiff_data)


def convert_to_png(image_bytes):
    out = BytesIO()

    i = Image.open(BytesIO(image_bytes))
    i.save(out, 'PNG')

    out.seek(0)
    output = out.read()

    logger.debug('to png converstion stats: '
                 f'length of input: {len(image_bytes)} '
                 f'length of output: {len(output)} ')
    return output
