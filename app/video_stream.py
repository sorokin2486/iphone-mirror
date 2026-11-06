# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Локальный TCP-сервер: принимает H.264 (Annex-B) от UxPlay и декодирует кадры."""
from __future__ import annotations

import logging
import socket
import threading

import av
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

log = logging.getLogger(__name__)

RECV_CHUNK = 256 * 1024
ACCEPT_TIMEOUT_S = 0.5


class LatestFrame:
    """Хранит только самый свежий кадр — UI никогда не отстаёт от телефона."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._image: QImage | None = None
        self._pending = False

    def put(self, image: QImage) -> bool:
        """Сохраняет кадр. True, если UI нужно уведомить (предыдущий уже забран)."""
        with self._lock:
            self._image = image
            notify = not self._pending
            self._pending = True
            return notify

    def take(self) -> QImage | None:
        with self._lock:
            self._pending = False
            return self._image


def frame_to_qimage(frame: av.VideoFrame) -> QImage:
    # При ширине, не кратной выравниванию libav (напр. 886), массив идёт с отступами —
    # QImage нужен непрерывный буфер.
    rgb = np.ascontiguousarray(frame.to_ndarray(format="rgb24"))
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()


class H264Decoder:
    """Обёртка над libavcodec: кормим байтами, получаем QImage."""

    def __init__(self) -> None:
        self._ctx = av.CodecContext.create("h264", "r")
        try:
            self._ctx.thread_type = "SLICE"   # без задержки на frame-threading
        except (AttributeError, ValueError):
            pass

    def feed(self, data: bytes) -> list[QImage]:
        images: list[QImage] = []
        for packet in self._ctx.parse(data):
            try:
                frames = self._ctx.decode(packet)
            except av.error.InvalidDataError:
                continue   # ждём следующий ключевой кадр
            images.extend(frame_to_qimage(f) for f in frames)
        return images


class VideoServer(QThread):
    frame_ready = Signal()            # забирать кадр через latest.take()
    stream_started = Signal()
    stream_ended = Signal()
    server_error = Signal(str)

    def __init__(self, port: int, parent=None) -> None:
        super().__init__(parent)
        self._port = port
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._active_streams = 0          # соединения, по которым уже идут кадры
        self._workers: list[threading.Thread] = []
        self.latest = LatestFrame()

    def stop(self) -> None:
        self._stop.set()
        self.wait(3000)

    def run(self) -> None:
        try:
            server = socket.create_server(("127.0.0.1", self._port))
        except OSError as exc:
            self.server_error.emit(f"Порт {self._port} занят или недоступен: {exc}")
            return
        server.settimeout(ACCEPT_TIMEOUT_S)
        with server:
            while not self._stop.is_set():
                try:
                    conn, _addr = server.accept()
                except socket.timeout:
                    continue
                except OSError as exc:
                    self.server_error.emit(f"Ошибка сокета: {exc}")
                    break
                # UxPlay держит соединение открытым с момента запуска, а при
                # переподключении iPhone может открыть новое раньше, чем закроет
                # старое, — поэтому каждое соединение обслуживается в своём потоке.
                worker = threading.Thread(target=self._serve_safe, args=(conn,), daemon=True)
                self._workers = [w for w in self._workers if w.is_alive()] + [worker]
                worker.start()
        for worker in self._workers:
            worker.join(2)

    def _serve_safe(self, conn: socket.socket) -> None:
        with conn:
            try:
                self._serve(conn)
            except Exception as exc:  # noqa: BLE001 - сервер должен пережить битый поток
                log.exception("Ошибка обработки видеопотока")
                self.server_error.emit(f"Ошибка видеопотока: {exc}")

    def _set_streaming(self, delta: int) -> None:
        with self._lock:
            before = self._active_streams
            self._active_streams = max(0, before + delta)
            after = self._active_streams
        if before == 0 and after > 0:
            self.stream_started.emit()
        elif before > 0 and after == 0:
            self.stream_ended.emit()

    def _serve(self, conn: socket.socket) -> None:
        conn.settimeout(ACCEPT_TIMEOUT_S)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        decoder = H264Decoder()
        started = False
        try:
            while not self._stop.is_set():
                try:
                    data = conn.recv(RECV_CHUNK)
                except socket.timeout:
                    continue
                except OSError as exc:
                    log.info("Видеопоток прерван: %s", exc)
                    break
                if not data:
                    break
                for image in decoder.feed(data):
                    if not started:
                        started = True
                        self._set_streaming(+1)
                    if self.latest.put(image):
                        self.frame_ready.emit()
        finally:
            if started:
                self._set_streaming(-1)
