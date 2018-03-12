import sys


class MustRunOnEitherMacOrLinux(Exception):
    pass


if sys.platform == 'darwin':
    from mac_clipboard import MacClipboard as LocalClipboard
elif sys.platform == 'linux':
    from linux_clipboard import LinuxClipboard as LocalClipboard
else:
    raise MustRunOnEitherMacOrLinux
