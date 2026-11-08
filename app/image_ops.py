# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Геометрия картинки в обычном окне: поворот, зеркало, вписать / растянуть / заполнить.

Кадры 60 раз в секунду не пересоздаются: поворот и зеркало применяются трансформацией
QPainter при отрисовке. Новое изображение строится только для скриншота.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSizeF
from PySide6.QtGui import QImage, QPainter, QTransform

from .config import FIT_MODES  # noqa: F401 — fit | stretch | fill (вписать | растянуть | заполнить)


def oriented_size(size: QSizeF, rotation: int) -> QSizeF:
    """Размер картинки после поворота на rotation × 90° по часовой."""
    return QSizeF(size.height(), size.width()) if rotation % 2 else QSizeF(size)


def target_rect(content: QSizeF, area: QRectF, mode: str) -> QRectF:
    """Куда рисовать картинку размера `content` внутри `area` в режиме `mode`."""
    if content.isEmpty() or area.isEmpty() or mode == "stretch":
        return QRectF(area)
    kx, ky = area.width() / content.width(), area.height() / content.height()
    k = max(kx, ky) if mode == "fill" else min(kx, ky)
    w, h = content.width() * k, content.height() * k
    return QRectF(area.center().x() - w / 2, area.center().y() - h / 2, w, h)


def paint_oriented(p: QPainter, image: QImage, area: QRectF, mode: str,
                   rotation: int, mirrored: bool) -> QRectF:
    """Рисует кадр с поворотом/зеркалом в `area`. Возвращает занятый прямоугольник."""
    rotation %= 4
    dest = target_rect(oriented_size(QSizeF(image.size()), rotation), area, mode)
    w, h = (dest.height(), dest.width()) if rotation % 2 else (dest.width(), dest.height())
    p.save()
    p.setClipRect(area)
    p.translate(dest.center())
    if mirrored:
        p.scale(-1, 1)          # зеркалим уже повёрнутую картинку (по горизонтали экрана)
    p.rotate(90 * rotation)
    p.drawImage(QRectF(-w / 2, -h / 2, w, h), image)
    p.restore()
    return dest.intersected(area)


def oriented_image(image: QImage, rotation: int, mirrored: bool) -> QImage:
    """Копия кадра в том виде, как он показан (для скриншота)."""
    t = QTransform()
    if mirrored:
        t.scale(-1, 1)
    t.rotate(90 * (rotation % 4))
    return image.transformed(t) if (rotation % 4 or mirrored) else image.copy()
