"""Геометрия и отрисовка корпуса «iPhone» (в портретных единицах, без Qt-виджетов)."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen

# Базовые размеры корпуса в «единицах» при scale=1 (пропорции ~ iPhone 15 Pro).
BODY_W = 430.0
BODY_H = 880.0
BODY_RADIUS = 68.0
FRAME_W = 5.0          # титановая рамка
BEZEL = 13.0           # чёрная рамка вокруг экрана
SCREEN_RADIUS = BODY_RADIUS - FRAME_W - BEZEL + 6
MARGIN = 14.0          # место под кнопки и тень
ISLAND_W, ISLAND_H, ISLAND_TOP = 122.0, 36.0, 12.0
BUTTON_DEPTH = 4.0

# (сторона, y, высота) — кнопки на корпусе
BUTTONS = (
    ("left", 170.0, 34.0),    # Action button
    ("left", 245.0, 66.0),    # громкость +
    ("left", 325.0, 66.0),    # громкость −
    ("right", 270.0, 104.0),  # питание
)

PALETTES = {
    "natural": ("#c9c4bb", "#8d8981", "#5d5a55"),
    "black":   ("#5b5c60", "#2e2f33", "#151618"),
    "white":   ("#f1f0ec", "#cfcdc8", "#9e9c97"),
    "blue":    ("#5d6878", "#3a4350", "#222831"),
}


@dataclass(frozen=True)
class PhoneLayout:
    """Прямоугольники в портретных координатах (до поворота)."""
    canvas: QRectF
    body: QRectF
    screen: QRectF
    island: QRectF

    @staticmethod
    def create(scale: float) -> "PhoneLayout":
        s = scale
        body = QRectF(MARGIN * s, MARGIN * s, BODY_W * s, BODY_H * s)
        inset = (FRAME_W + BEZEL) * s
        screen = body.adjusted(inset, inset, -inset, -inset)
        island = QRectF(screen.center().x() - ISLAND_W * s / 2, screen.top() + ISLAND_TOP * s,
                        ISLAND_W * s, ISLAND_H * s)
        canvas = QRectF(0, 0, (BODY_W + 2 * MARGIN) * s, (BODY_H + 2 * MARGIN) * s)
        return PhoneLayout(canvas, body, screen, island)


def rounded(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def screen_path(layout: PhoneLayout, scale: float) -> QPainterPath:
    return rounded(layout.screen, SCREEN_RADIUS * scale)


def paint_shadow(p: QPainter, layout: PhoneLayout, scale: float) -> None:
    p.setPen(Qt.NoPen)
    steps = 8
    for i in range(steps):
        grow = (steps - i) * 1.2 * scale
        alpha = 6 + i * 3
        p.setBrush(QColor(0, 0, 0, alpha))
        r = layout.body.adjusted(-grow, -grow + 3 * scale, grow, grow + 3 * scale)
        p.drawPath(rounded(r, (BODY_RADIUS + grow / scale) * scale))


def paint_buttons(p: QPainter, layout: PhoneLayout, scale: float, color: str) -> None:
    light, mid, dark = PALETTES[color]
    p.setPen(Qt.NoPen)
    for side, y, h in BUTTONS:
        top = layout.body.top() + y * scale
        if side == "left":
            rect = QRectF(layout.body.left() - BUTTON_DEPTH * scale, top, BUTTON_DEPTH * scale + 2, h * scale)
        else:
            rect = QRectF(layout.body.right() - 2, top, BUTTON_DEPTH * scale + 2, h * scale)
        grad = QLinearGradient(rect.topLeft(), rect.topRight())
        grad.setColorAt(0, QColor(dark))
        grad.setColorAt(0.5, QColor(light))
        grad.setColorAt(1, QColor(dark))
        p.setBrush(grad)
        p.drawRoundedRect(rect, 2 * scale, 2 * scale)


def paint_body(p: QPainter, layout: PhoneLayout, scale: float, color: str) -> None:
    light, mid, dark = PALETTES[color]
    body = layout.body
    # Титановая рамка: диагональный градиент с бликами.
    grad = QLinearGradient(body.topLeft(), body.bottomRight())
    grad.setColorAt(0.0, QColor(light))
    grad.setColorAt(0.25, QColor(mid))
    grad.setColorAt(0.5, QColor(light))
    grad.setColorAt(0.75, QColor(dark))
    grad.setColorAt(1.0, QColor(mid))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawPath(rounded(body, BODY_RADIUS * scale))
    # Тонкая тёмная кромка снаружи.
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(0, 0, 0, 140), max(1.0, 0.8 * scale)))
    p.drawPath(rounded(body, BODY_RADIUS * scale))
    # Чёрное стекло (рамка вокруг экрана).
    glass = body.adjusted(FRAME_W * scale, FRAME_W * scale, -FRAME_W * scale, -FRAME_W * scale)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#050505"))
    p.drawPath(rounded(glass, (BODY_RADIUS - FRAME_W) * scale))


def paint_island(p: QPainter, layout: PhoneLayout, scale: float, active: bool) -> None:
    isl = layout.island
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#000000"))
    p.drawRoundedRect(isl, isl.height() / 2, isl.height() / 2)
    # «Камера» в правой части острова.
    cam_r = isl.height() * 0.22
    cam = QPointF(isl.right() - isl.height() / 2, isl.center().y())
    p.setBrush(QColor("#0d1018"))
    p.drawEllipse(cam, cam_r, cam_r)
    p.setBrush(QColor(40, 60, 110, 160))
    p.drawEllipse(cam, cam_r * 0.45, cam_r * 0.45)
    if active:   # зелёный индикатор «идёт трансляция»
        p.setBrush(QColor("#30d158"))
        dot = QPointF(isl.left() + isl.height() / 2, isl.center().y())
        p.drawEllipse(dot, isl.height() * 0.11, isl.height() * 0.11)


def paint_glass_glare(p: QPainter, layout: PhoneLayout, scale: float) -> None:
    grad = QLinearGradient(layout.screen.topLeft(), layout.screen.bottomRight())
    grad.setColorAt(0.0, QColor(255, 255, 255, 18))
    grad.setColorAt(0.35, QColor(255, 255, 255, 0))
    grad.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawPath(screen_path(layout, scale))
