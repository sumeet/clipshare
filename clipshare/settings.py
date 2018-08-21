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


class cached_classproperty:

    class UNSET: pass

    def __init__(self, func):
        self._func = func
        self._value = self.UNSET

    def __get__(self, instance, cls):
        if self._value is not self.UNSET:
            return self._value
        self._value = self._func(cls)
        return self._value


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


from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QVBoxLayout


QT_WIDGET_BY_FIELD_TYPE = {
    Boolean: QCheckBox,
    IP: QLineEdit,
    Port: QLineEdit,
    WebsocketURL: QLineEdit,
}


class SettingsWindow:

    # TODO: actually accept a settings object instead of defaulting
    def __init__(self, settings=Settings.default):
        self._settings = settings
        self._qdialog = QDialog()
        self._qdialog.setWindowTitle('Clipshare settings')
        self._qdialog.accepted.connect(self._accept)

    # awaitable
    def show(self):
        self._qt_form = self._build_qt_form()
        self._render()

        future = asyncio.Future()
        self._qdialog.finished.connect(lambda result: future.set_result(None))

        self._qdialog.exec_()
        return future

    def _render(self):
        self._qt_form = self._build_qt_form()

        main_layout = QVBoxLayout()

        form_groupbox = QWidget()
        form_groupbox.setLayout(self._qt_form.qlayout)
        main_layout.addWidget(form_groupbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                      QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._qdialog.accept)
        button_box.rejected.connect(self._qdialog.reject)
        main_layout.addWidget(button_box)

        old_qlayout = self._qdialog.layout()
        if old_qlayout:
            # reparenting the old layout to a temporary widget will reparent the
            # old layout, allowing us to set a new one.
            # see https://stackoverflow.com/a/10439207/149987
            QWidget().setLayout(old_qlayout)
        self._qdialog.setLayout(main_layout)

    def _accept(self):
        self._pull_settings_from_qt_form()
        AppSettings.set(self._settings)

    def _build_qt_form(self):
        fields = SettingsForm(self._settings).fields
        qt_form = QtForm.build(fields)

        for qcheckbox_widget in qt_form.qcheckbox_widgets:
            qcheckbox_widget.stateChanged.connect(
                lambda state: self._pull_settings_from_qt_form())
        return qt_form

    def _pull_settings_from_qt_form(self):
        self._settings = build_settings_from_qt_form(self._qt_form)
        self._render()


class QtForm:

    @classmethod
    def build(cls, form_fields):
        layout = QFormLayout()
        qwidgets_by_label_text = {}
        for field in form_fields:
            qwidget = QT_WIDGET_BY_FIELD_TYPE[field.type_cls]()
            cls._set_widget_value(qwidget, field.value)
            qwidget.setDisabled(field.disabled)

            layout.addRow(QLabel(field.label_text), qwidget)
            qwidgets_by_label_text[field.label_text] = qwidget
        return cls(layout, qwidgets_by_label_text)

    def __init__(self, qformlayout, qwidgets_by_label_text):
        self._qformlayout = qformlayout
        self._qwidgets_by_label_text = qwidgets_by_label_text

    @property
    def qlayout(self):
        return self._qformlayout

    @property
    def field_values(self):
        return {label_text: self._get_widget_value(widget)
                for label_text, widget in self._qwidgets_by_label_text.items()}

    @property
    def qcheckbox_widgets(self):
        return (qwidget for qwidget in self._qwidgets_by_label_text.values() if
                isinstance(qwidget, QCheckBox))

    def _get_widget_value(self, qwidget):
        if isinstance(qwidget, QCheckBox):
            return qwidget.isChecked()
        if isinstance(qwidget, QLineEdit):
            return qwidget.text()
        raise Exception(f'unknown widget type: {qwidget}')

    @classmethod
    def _set_widget_value(cls, qwidget, value):
        if isinstance(qwidget, QCheckBox):
            return qwidget.setChecked(value)
        if isinstance(qwidget, QLineEdit):
            return qwidget.setText(value)
        raise Exception(f'unknown widget type: {qwidget}')


def build_settings_from_qt_form(qt_form):
    field_values = qt_form.field_values
    return Settings(
        is_server_enabled=field_values['Server enabled'],
        server_listen_ip=field_values['Server bind IP'],
        server_listen_port=field_values['Server bind port'],
        is_client_enabled=field_values['Client enabled'],
        client_ws_url=field_values['Websocket URL of server to connect to'])
