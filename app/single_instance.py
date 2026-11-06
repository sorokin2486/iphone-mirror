"""Один экземпляр приложения: повторный запуск показывает уже открытое окно.

Две копии запускали бы два UxPlay с одним именем и портами — iPhone видел бы
приёмник, но не мог к нему подключиться.
"""
from __future__ import annotations

import getpass

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

CONNECT_TIMEOUT_MS = 500
ACTIVATE = b"activate"


def server_name() -> str:
    try:
        user = getpass.getuser()
    except (KeyError, OSError):
        user = "user"
    return f"iPhoneMirror-{user}"


def notify_running_instance(name: str | None = None) -> bool:
    """True, если другой экземпляр уже работает (и ему отправлена просьба показать окно)."""
    sock = QLocalSocket()
    sock.connectToServer(name or server_name())
    if not sock.waitForConnected(CONNECT_TIMEOUT_MS):
        return False
    sock.write(ACTIVATE)
    sock.waitForBytesWritten(CONNECT_TIMEOUT_MS)
    sock.disconnectFromServer()
    return True


class InstanceServer(QObject):
    activate_requested = Signal()

    def __init__(self, name: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._name = name or server_name()
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)

    def listen(self) -> bool:
        if self._server.listen(self._name):
            return True
        # Остался «мёртвый» сокет от упавшего экземпляра — убираем и пробуем снова.
        QLocalServer.removeServer(self._name)
        return self._server.listen(self._name)

    def _on_connection(self) -> None:
        # Само подключение второго экземпляра и есть просьба показать окно:
        # клиент может успеть отключиться раньше, чем мы прочитаем данные.
        while (sock := self._server.nextPendingConnection()) is not None:
            sock.disconnected.connect(sock.deleteLater)
            self.activate_requested.emit()
