"""Виджет, рисующий iPhone с транслируемым экраном внутри."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QTransform
from PySide6.QtWidgets import QWidget

from . import phone_skin as skin
from .lock_screen import paint_lock_screen

CLOCK_REFRESH_MS = 15_000


def fit_rect(image_size: QSize, target: QRectF) -> QRectF:
    """Вписывает изображение в target с сохранением пропорций (по центру)."""
    if image_size.isEmpty():
        return QRectF(target)
    k = min(target.width() / image_size.width(), target.height() / image_size.height())
    w, h = image_size.width() * k, image_size.height() * k
    return QRectF(target.center().x() - w / 2, target.center().y() - h / 2, w, h)


class PhoneView(QWidget):
    def __init__(self, scale: float, color: str, device_name: str, parent=None) -> None:
        super().__init__(parent)
        self._scale = scale
        self._color = color
        self._device_name = device_name
        self._image: QImage | None = None
        self._status = "running"
        self._streaming = False
        self._link_kind: str | None = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._clock = QTimer(self, interval=CLOCK_REFRESH_MS, timeout=self.update)
        self._clock.start()
        self._apply_size()

    # --- публичное API -----------------------------------------------------
    @property
    def landscape(self) -> bool:
        img = self._image
        return self._streaming and img is not None and img.width() > img.height()

    @property
    def current_image(self) -> QImage | None:
        return self._image if self._streaming else None

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self._apply_size()

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def set_device_name(self, name: str) -> None:
        self._device_name = name
        self.update()

    def set_status(self, status: str) -> None:
        self._status = status
        self.update()

    def set_link(self, link_kind: str | None) -> None:
        self._link_kind = link_kind
        self.update()

    def set_streaming(self, streaming: bool) -> None:
        self._streaming = streaming
        if not streaming:
            self._image = None
        self._apply_size()

    def show_frame(self, image: QImage) -> None:
        was_landscape = self.landscape
        self._image = image
        self._streaming = True
        if self.landscape != was_landscape:
            self._apply_size()
        self.update()

    # --- размер/повороты ---------------------------------------------------
    def _apply_size(self) -> None:
        canvas = skin.PhoneLayout.create(self._scale).canvas
        w, h = round(canvas.width()), round(canvas.height())
        self.setFixedSize(QSize(h, w) if self.landscape else QSize(w, h))
        self.update()

    def _transform(self, layout: skin.PhoneLayout) -> QTransform:
        if not self.landscape:
            return QTransform()
        # Поворот на -90°: верх телефона (Dynamic Island) уходит влево.
        return QTransform().translate(0, layout.canvas.width()).rotate(-90)

    # --- отрисовка ---------------------------------------------------------
    def paintEvent(self, _event) -> None:
        layout = skin.PhoneLayout.create(self._scale)
        s = self._scale
        t = self._transform(layout)
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        p.setTransform(t)
        skin.paint_shadow(p, layout, s)
        skin.paint_buttons(p, layout, s, self._color)
        skin.paint_body(p, layout, s, self._color)
        p.save()
        p.setClipPath(skin.screen_path(layout, s))
        if self._streaming and self._image is not None:
            self._paint_video(p, layout, t)
        else:
            paint_lock_screen(p, layout.screen, self._status, self._device_name, self._link_kind)
        p.restore()
        p.setTransform(t)
        skin.paint_island(p, layout, s, active=self._streaming)
        skin.paint_glass_glare(p, layout, s)
        p.end()

    def _paint_video(self, p: QPainter, layout: skin.PhoneLayout, t: QTransform) -> None:
        p.fillRect(layout.screen, QColor("#000"))
        # Видео рисуем в экранных координатах виджета (без поворота).
        target = t.mapRect(layout.screen)
        p.setTransform(QTransform())
        p.setClipPath(t.map(skin.screen_path(layout, self._scale)))
        p.drawImage(fit_rect(self._image.size(), target), self._image)
