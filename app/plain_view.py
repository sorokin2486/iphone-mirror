# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Видеообласть обычного окна: кадр с поворотом/зеркалом/режимом вписывания или заглушка."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from .image_ops import oriented_image, oriented_size, paint_oriented
from .lock_screen import LINK_BADGE, LINK_TEXT, STATUS_TEXT

BACKGROUND = QColor("#0e0d12")
CARD = QColor(255, 255, 255, 18)
TEXT = QColor("#e9e4f5")
MUTED = QColor("#9b91b3")
BADGE = QColor("#30d158")
ICON_FONT = "Segoe Fluent Icons"
PHONE_GLYPH = ""
DEFAULT_ASPECT = QSizeF(9, 19.5)       # портрет iPhone, пока нет кадров


class PlainView(QWidget):
    double_clicked = Signal()
    menu_requested = Signal(QPoint)

    def __init__(self, device_name: str, fit_mode: str, rotation: int, mirrored: bool, parent=None) -> None:
        super().__init__(parent)
        self._device_name = device_name
        self._fit_mode = fit_mode
        self._rotation = rotation % 4
        self._mirrored = mirrored
        self._image: QImage | None = None
        self._streaming = False
        self._status = "running"
        self._link_kind: str | None = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(160, 160)
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    # --- состояние ------------------------------------------------------------
    @property
    def current_image(self) -> QImage | None:
        return self._image if self._streaming else None

    def displayed_image(self) -> QImage | None:
        img = self.current_image
        return oriented_image(img, self._rotation, self._mirrored) if img is not None else None

    def content_aspect(self) -> QSizeF:
        """Пропорции того, что сейчас видно (с учётом поворота)."""
        base = QSizeF(self._image.size()) if self.current_image is not None else DEFAULT_ASPECT
        return oriented_size(base, self._rotation)

    def set_transform(self, fit_mode: str, rotation: int, mirrored: bool) -> None:
        self._fit_mode, self._rotation, self._mirrored = fit_mode, rotation % 4, mirrored
        self.update()

    def set_device_name(self, name: str) -> None:
        self._device_name = name
        self.update()

    def set_status(self, status: str) -> None:
        self._status = status
        self.update()

    def set_link(self, kind: str | None) -> None:
        self._link_kind = kind
        self.update()

    def set_streaming(self, active: bool) -> None:
        self._streaming = active
        if not active:
            self._image = None
        self.update()

    def show_frame(self, image: QImage) -> None:
        self._image = image
        self._streaming = True
        self.update()

    # --- события ------------------------------------------------------------
    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self.double_clicked.emit()

    def contextMenuEvent(self, e) -> None:
        self.menu_requested.emit(e.globalPos())

    # --- отрисовка ----------------------------------------------------------
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        area = QRectF(self.rect())
        p.fillRect(area, BACKGROUND)
        if self.current_image is not None:
            paint_oriented(p, self._image, area, self._fit_mode, self._rotation, self._mirrored)
        else:
            self._paint_placeholder(p, area)
        p.end()

    def _paint_placeholder(self, p: QPainter, area: QRectF) -> None:
        card = QRectF(0, 0, min(area.width() - 24, 420), min(area.height() - 24, 230))
        card.moveCenter(area.center())
        p.setPen(Qt.NoPen)
        p.setBrush(CARD)
        p.drawRoundedRect(card, 18, 18)

        icon = QRectF(card.left(), card.top() + card.height() * 0.12, card.width(), card.height() * 0.42)
        p.setPen(MUTED)
        p.setFont(QFont(ICON_FONT, max(8, int(icon.height() * 0.45))))
        p.drawText(icon, Qt.AlignCenter, PHONE_GLYPH)

        template = STATUS_TEXT.get(self._status, STATUS_TEXT["running"])
        if self._status == "running" and self._link_kind in LINK_TEXT:
            template = LINK_TEXT[self._link_kind]
        text_rect = QRectF(card.left() + 16, icon.bottom(), card.width() - 32, card.bottom() - icon.bottom() - 12)
        font = QFont("Segoe UI")
        font.setPixelSize(max(11, min(17, int(card.width() / 24))))
        p.setFont(font)
        p.setPen(TEXT)
        p.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   template.format(name=self._device_name))

        if self._link_kind in LINK_BADGE:
            badge_font = QFont("Segoe UI", 9, QFont.DemiBold)
            p.setFont(badge_font)
            label = LINK_BADGE[self._link_kind]
            w = p.fontMetrics().horizontalAdvance(label) + 18
            badge = QRectF(card.right() - w - 12, card.top() + 12, w, 22)
            p.setPen(Qt.NoPen)
            p.setBrush(BADGE)
            p.drawRoundedRect(badge, 11, 11)
            p.setPen(Qt.white)
            p.drawText(badge, Qt.AlignCenter, label)
