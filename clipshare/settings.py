import asyncio
from collections import namedtuple

from PyQt5.QtCore import QSettings


Settings = namedtuple('Settings',
                      ['is_server_enabled',
                       'server_listen_ip',
                       'server_listen_port',
                       'is_client_enabled',
                       'client_ws_url'])

Settings.default = Settings(is_server_enabled=False, server_listen_ip='',
                            server_listen_port='', is_client_enabled=False,
                            client_ws_url='')


class classproperty:

    def __init__(self, func):
        self._func = func

    def __get__(self, instance, cls):
        return self._func(cls)


# global object holding app settings stored in QSettings
class AppSettings:

    @classproperty
    def get(cls):
        qsettings = cls._qsettings
        return Settings(
            is_server_enabled=qsettings.value('is_server_enabled', type=bool),
            server_listen_ip=qsettings.value('server_listen_ip', type=str),
            server_listen_port=qsettings.value('server_listen_port', type=str),
            is_client_enabled=qsettings.value('is_client_enabled', type=bool),
            client_ws_url=qsettings.value('client_ws_url', type=str))

    @classmethod
    def set(cls, settings):
        qsettings = cls._qsettings
        qsettings.setValue('is_server_enabled', settings.is_server_enabled)
        qsettings.setValue('server_listen_ip', settings.server_listen_ip)
        qsettings.setValue('server_listen_port', settings.server_listen_port)
        qsettings.setValue('is_client_enabled', settings.is_client_enabled)
        qsettings.setValue('client_ws_url', settings.client_ws_url)

    _qsettings = QSettings('sumeet', 'clipshare')


class Boolean: pass
class IP: pass
class Port: pass
class WebsocketURL: pass


class SettingsForm:

    def __init__(self, settings):
        self._settings = settings

    @property
    def fields(self):
        return [
            # TODO: add groups in here for server settings and client settings
            FormField(Boolean, 'Server enabled',
                      self._settings.is_server_enabled),
            FormField(IP, 'Server bind IP', self._settings.server_listen_ip,
                      disabled=not self._settings.is_server_enabled),
            FormField(Port, 'Server bind port',
                      self._settings.server_listen_port,
                      disabled=not self._settings.is_server_enabled),
            FormField(Boolean, 'Client enabled',
                      self._settings.is_client_enabled),
            FormField(WebsocketURL, 'Websocket URL of server to connect to',
                      self._settings.client_ws_url,
                      disabled=not self._settings.is_client_enabled),
        ]


class FormField(namedtuple('FormField', 'type_cls label_text value disabled')):

    def __new__(cls, type_cls, label_text, value, disabled=False):
        return super().__new__(cls, type_cls, label_text, value, disabled)
