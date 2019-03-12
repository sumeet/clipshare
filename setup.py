import sys

from setuptools import setup


dependencies = [
    # TODO: pyqt5 isn't actually required for the server component, and it's a
    # big dependency. maybe there's a way to skip this if someone just wants to
    # install the server?

    # qt5 used for the UI for both mac and linux
    'pyqt5',
    # quamash makes qt's event loop usable with python
    'quamash',
    'websockets',
    'Pillow',
    'blinker',
    'asyncblink',
    'async_generator',
    'cached_property',
    'tenacity',
    # for mac, we use pyobjc (ScriptingBridge) to access the clipboard. on
    # linux, we use pyqt5
    'pyobjc;platform_system=="Darwin"']


setup(
    name='clipshare',
    version='0.1',
    packages=['clipshare'],
    description='Sync clipboard text and images between computers.',
    url='https://github.com/sumeet/clipshare',
    license='GPL',
    author='Sumeet Agarwal',
    author_email='sumeet.a@gmail.com',
    # need to include the colored icons used for the GUI
    package_data={'': ['*.png']},
    python_requires='>=3.6',
    scripts=['bin/clipsharec'],
    install_requires=dependencies,
    zip_safe=False)
