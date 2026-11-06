"""Чистая логика масштабирования окна: зоны захвата краёв и расчёт масштаба при перетаскивании."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSizeF

from . import phone_skin as skin
from .config import SCALE_MAX, SCALE_MIN

GRIP_PX = 12.0          # ширина зоны захвата вокруг края корпуса
PRESETS_PERCENT = (50, 75, 100, 125, 150)


def edge_at(pos: QPointF, body: QRectF, grip: float = GRIP_PX) -> str:
    """Какой край корпуса под курсором: "", "left", "topright" и т.п."""
    if not (body.left() - grip <= pos.x() <= body.right() + grip
            and body.top() - grip <= pos.y() <= body.bottom() + grip):
        return ""
    vertical = ("top" if abs(pos.y() - body.top()) <= grip
                else "bottom" if abs(pos.y() - body.bottom()) <= grip else "")
    horizontal = ("left" if abs(pos.x() - body.left()) <= grip
                  else "right" if abs(pos.x() - body.right()) <= grip else "")
    return vertical + horizontal


def scale_from_drag(edge: str, start_scale: float, start_size: QSizeF, dx: float, dy: float) -> float:
    """Новый масштаб при перетаскивании края `edge` на (dx, dy). Пропорции сохраняются."""
    if not edge or start_size.isEmpty():
        return start_scale
    sx = dx if "right" in edge else -dx if "left" in edge else None
    sy = dy if "bottom" in edge else -dy if "top" in edge else None
    fx = (start_size.width() + sx) / start_size.width() if sx is not None else None
    fy = (start_size.height() + sy) / start_size.height() if sy is not None else None
    if fx is None:
        factor = fy
    elif fy is None:
        factor = fx
    else:   # угол: берём то направление, куда тянут сильнее
        factor = fx if abs(fx - 1) >= abs(fy - 1) else fy
    return start_scale * max(factor, 0.05)


def max_scale_for(available: QSizeF, landscape: bool) -> float:
    """Наибольший масштаб, при котором окно целиком помещается на экране."""
    w1 = skin.BODY_W + 2 * skin.MARGIN
    h1 = skin.BODY_H + 2 * skin.MARGIN
    if landscape:
        w1, h1 = h1, w1
    fit = min(available.width() / w1, available.height() / h1)
    return max(SCALE_MIN, min(SCALE_MAX, fit))


def clamp_scale(scale: float, max_scale: float) -> float:
    return round(min(max(scale, SCALE_MIN), max_scale), 3)


def anchored_pos(edge: str, start_geom: QRectF, new_size: QSizeF) -> QPointF:
    """Позиция окна, при которой противоположный от `edge` край остаётся на месте."""
    x = start_geom.right() - new_size.width() if "left" in edge else start_geom.left()
    y = start_geom.bottom() - new_size.height() if "top" in edge else start_geom.top()
    return QPointF(x, y)
