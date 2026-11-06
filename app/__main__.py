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
from .single_instance import InstanceServer, notify_running_instance
from .usb_link import LinkMonitor
from .receiver import UxPlayReceiver
from .video_stream import VideoServer


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

    state = {"cfg": load_config()}
    receiver = UxPlayReceiver(state["cfg"])
    server = VideoServer(state["cfg"].video_port)
    window = MirrorWindow(state["cfg"], lambda: receiver.lines)
    links = LinkMonitor()
    view = window.view

    def on_frame() -> None:
        image = server.latest.take()
        if image is None:
            return
        was_landscape = view.landscape
        view.show_frame(image)
        if view.landscape != was_landscape:
            window.refit()

    def on_stream(active: bool) -> None:
        view.set_streaming(active)
        if not active and receiver.is_running():
            view.set_status("running")
        window.refit()

    def on_config(cfg: AppConfig) -> None:
        state["cfg"] = cfg
        receiver.update_config(cfg)
        save_config(cfg)

    server.frame_ready.connect(on_frame)
    server.stream_started.connect(lambda: on_stream(True))
    server.stream_ended.connect(lambda: on_stream(False))
    server.server_error.connect(lambda msg: (receiver.log_line.emit(msg), view.set_status("error")))
    receiver.status_changed.connect(view.set_status)
    receiver.client_event.connect(lambda ev: view.set_status("connecting") if ev == "connecting" else None)
    receiver.log_line.connect(window.append_log)
    window.config_changed.connect(on_config)
    window.restart_requested.connect(receiver.restart)

    def on_link(link) -> None:
        window.set_link(link)
        receiver.log_line.emit(f"Прямое подключение к iPhone: {link}" if link else "Прямое подключение к iPhone: нет")
        # Новый сетевой интерфейс: перезапускаем UxPlay, чтобы его mDNS-объявление
        # дошло и по кабелю. Во время трансляции не трогаем.
        if link is not None and receiver.is_running() and view.current_image is None:
            receiver.restart()

    links.link_changed.connect(on_link)

    def activate() -> None:
        window.showNormal()
        window.raise_()
        window.activateWindow()

    instance.activate_requested.connect(activate)

    def shutdown() -> None:
        receiver.stop()
        server.stop()
        pos = window.pos()
        save_config(state["cfg"].with_changes(window_x=pos.x(), window_y=pos.y()))

    app.aboutToQuit.connect(shutdown)
    server.start()
    receiver.start()
    window.show()
    links.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
