# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Точка входа: python -m app"""
from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import __author__, __brand__, __version__
from .config import AppConfig, load_config, save_config
from .main_window import MirrorWindow
from .paths import ICON_PATH
from .plain_window import PlainWindow
from .receiver import UxPlayReceiver
from .single_instance import InstanceServer, notify_running_instance
from .usb_link import LinkMonitor
from .video_stream import VideoServer

WINDOW_CLASSES = {"phone": MirrorWindow, "window": PlainWindow}


class DisplayController:
    """Держит активное окно (iPhone или обычное) и переключает их без разрыва трансляции."""

    def __init__(self, cfg: AppConfig, receiver: UxPlayReceiver) -> None:
        self.cfg = cfg
        self.receiver = receiver
        self.status = "running"
        self.link = None
        self.last_image = None
        self.window = self._make(cfg.view_mode)

    def _make(self, mode: str):
        win = WINDOW_CLASSES[mode](self.cfg, lambda: self.receiver.lines)
        win.config_changed.connect(self.on_config)
        win.restart_requested.connect(self.receiver.restart)
        win.mode_requested.connect(self.switch)
        return win

    def on_config(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.receiver.update_config(cfg)
        save_config(cfg)

    def switch(self, mode: str) -> None:
        old = self.window
        if isinstance(old, WINDOW_CLASSES[mode]):
            return
        old.save_geometry()
        self.on_config(self.cfg.with_changes(view_mode=mode))
        new = self._make(mode)
        new.set_link(self.link)
        new.set_status(self.status)
        if self.last_image is not None:
            new.show_frame(self.last_image)
        self.window = new
        new.show()
        old.close()
        old.deleteLater()

    # --- события от приёмника и видео -----------------------------------------
    def on_frame(self, image) -> None:
        self.last_image = image
        self.window.show_frame(image)

    def on_stream(self, active: bool) -> None:
        if not active:
            self.last_image = None
        self.window.set_streaming(active)
        if not active and self.receiver.is_running():
            self.set_status("running")

    def set_status(self, status: str) -> None:
        self.status = status
        self.window.set_status(status)

    def set_link(self, link) -> None:
        self.link = link
        self.window.set_link(link)

    def activate(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("iPhone Mirror")
    app.setApplicationVersion(__version__)
    app.setOrganizationName(f"{__author__} ({__brand__})")
    if ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(ICON_PATH)))

    if notify_running_instance():
        return 0   # уже запущено — то окно само покажется
    instance = InstanceServer()
    instance.listen()

    cfg = load_config()
    receiver = UxPlayReceiver(cfg)
    server = VideoServer(cfg.video_port)
    display = DisplayController(cfg, receiver)
    links = LinkMonitor()

    def on_frame() -> None:
        image = server.latest.take()
        if image is not None:
            display.on_frame(image)

    server.frame_ready.connect(on_frame)
    server.stream_started.connect(lambda: display.on_stream(True))
    server.stream_ended.connect(lambda: display.on_stream(False))
    server.server_error.connect(lambda msg: (receiver.log_line.emit(msg), display.set_status("error")))
    receiver.status_changed.connect(display.set_status)
    receiver.client_event.connect(lambda ev: display.set_status("connecting") if ev == "connecting" else None)
    receiver.log_line.connect(lambda line: display.window.append_log(line))

    def on_link(link) -> None:
        display.set_link(link)
        receiver.log_line.emit(f"Прямое подключение к iPhone: {link}" if link else "Прямое подключение к iPhone: нет")
        # Новый сетевой интерфейс: перезапускаем UxPlay, чтобы его mDNS-объявление
        # дошло и по кабелю. Во время трансляции не трогаем.
        if link is not None and receiver.is_running() and not display.window.is_streaming:
            receiver.restart()

    links.link_changed.connect(on_link)
    instance.activate_requested.connect(display.activate)

    def shutdown() -> None:
        receiver.stop()
        server.stop()
        display.window.save_geometry()
        save_config(display.cfg)

    app.aboutToQuit.connect(shutdown)
    server.start()
    receiver.start()
    display.window.show()
    links.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
