import itertools
import logging
import pickle
import pprint
import sys
import time


color_codes = {'black': '0;30',
               'blue': '0;34',
               'green': '0;32',
               'cyan': '0;36',
               'red': '0;31',
               'purple': '0;35',
               'brown': '0;33',
               'light_gray': '0;37',
               'dark_gray': '1;30',
               'light_blue': '1;34',
               'light_green': '1;32',
               'light_cyan': '1;36',
               'light_red': '1;31',
               'light_purple': '1;35',
               'yellow': '1;33',
               'white': '1;37'}

for hard_to_read_or_distinguish_color in ['black', 'light_gray', 'dark_gray', 'white']:
    del color_codes[hard_to_read_or_distinguish_color]

def colorize(color, str):
    return f'\033[{color_codes[color]};1m{str}\033[0m'

class ConsistentColorer:

    def __init__(self):
        self._consistent_coloring_by_term = {}
        self._cycle_through_the_colors = itertools.cycle(color_codes.keys())

    def get_color_for(self, term):
        try:
            return self._consistent_coloring_by_term[term]
        except KeyError:
            next_color = next(self._cycle_through_the_colors)
            self._consistent_coloring_by_term[term] = next_color
            return next_color


class Highlighter:

    def __init__(self):
        self._consistent_colorer = ConsistentColorer()

    def format(self, record):
        logger_name = record.name
        color = self._consistent_colorer.get_color_for(logger_name)
        return (f'{self._padding}{self._format_time(record)} '
                f'{colorize(color, logger_name)} {self._format_body(record)}')

    def _format_body(self, record):
        return (self._format_exception(record.exc_info) if record.exc_info else
                record.getMessage())

    def _format_time(self, record):
        ct = time.localtime(record.created)
        t = time.strftime('%H:%M:%S', ct)
        return '%s,%03d' % (t, record.msecs)

    def _format_exception(self, exc_info):
        formatter = logging.Formatter()
        return f'Encountered an exception:\n{formatter.formatException(exc_info)}'

    @property
    def _padding(self):
        # add a couple of empty lines at the very beginning of the program
        if not hasattr(self, '_padding_done'):
            self._padding_done = True
            return '\n' * 2
        else:
            return ''


handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(Highlighter())


def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    # TODO: make this configurable
    logger.setLevel(logging.DEBUG)
    return logger


# wupz
getLogger = get_logger


def format_obj(o):
    contents = pprint.pformat(maybe_trunc(o))
    if '\n' not in contents:
        return contents
    # if the content is multiline, then prefix it with a newline to set the
    # entire output apart together
    output = '\n'
    for line in contents.splitlines():
        output += f'\t{line}\n'
    return output


TRUNC_AT_CHARS = 30
# takes any object and makes it look decently printable, truncating huge strings
def maybe_trunc(o):
    if isinstance(o, dict):
        return {k: maybe_trunc(v) for k, v in o.items()}
    if isinstance(o, (bytes, str)):
        try:
            # if we get a pickle string, try to unpickle it and show what's inside
            depickled = pickle.loads(o)
            return f'Pickle containing {maybe_trunc(depickled)}'
        except:
            length = len(o)
            if length < TRUNC_AT_CHARS:
                return o
            return str(o[:TRUNC_AT_CHARS]) + f'… ({length} total)'
    # if we don't have any special handling for that type, then just truncate its repr
    return maybe_trunc(repr(o))
