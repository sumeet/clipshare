from collections import namedtuple


class ProgressSignaler:

    def __init__(self, signal):
        self._progress = None
        self._signal = signal

    def begin_transfer(self, message):
        self._progress = TransferProgress(total=message.num_chunks, completed=0)
        self._signal.send(self._progress)

    def on_chunk_transferred(self):
        self._progress = self._progress.increment_completed
        self._signal.send(self._progress)


class TransferProgress(namedtuple('TransferProgress', 'total completed')):

    @property
    def increment_completed(self):
        return self._replace(completed=self.completed + 1)

    @property
    def is_complete(self):
        return self.total == self.completed
