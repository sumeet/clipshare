from io import BytesIO
from PIL import Image

import log


logger = log.get_logger(__name__)


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
