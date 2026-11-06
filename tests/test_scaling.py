# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Тесты масштабирования окна."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, QSizeF, Qt

from app.config import SCALE_MAX, SCALE_MIN, AppConfig
from app.scaling import anchored_pos, clamp_scale, edge_at, max_scale_for, scale_from_drag

BODY = QRectF(100, 100, 400, 800)


@pytest.mark.parametrize("pos,expected", [
    (QPointF(300, 500), ""),              # середина экрана — не край
    (QPointF(100, 500), "left"),
    (QPointF(505, 500), "right"),         # чуть снаружи — в зоне тени
    (QPointF(300, 95), "top"),
    (QPointF(300, 900), "bottom"),
    (QPointF(502, 898), "bottomright"),
    (QPointF(98, 103), "topleft"),
    (QPointF(10, 10), ""),                # далеко за пределами
])
def test_edge_at(pos, expected):
    assert edge_at(pos, BODY) == expected


def test_drag_right_edge_grows_proportionally():
    assert scale_from_drag("right", 1.0, QSizeF(400, 800), 100, 0) == pytest.approx(1.25)


def test_drag_left_edge_inward_shrinks():
    assert scale_from_drag("left", 1.0, QSizeF(400, 800), 100, 0) == pytest.approx(0.75)


def test_corner_uses_dominant_direction():
    assert scale_from_drag("bottomright", 1.0, QSizeF(400, 800), 10, 400) == pytest.approx(1.5)


def test_no_edge_keeps_scale():
    assert scale_from_drag("", 0.8, QSizeF(400, 800), 50, 50) == 0.8


def test_max_scale_fits_screen_height():
    s = max_scale_for(QSizeF(1920, 1040), landscape=False)
    assert s == pytest.approx(1040 / 908, rel=1e-3)
    assert max_scale_for(QSizeF(1920, 1040), landscape=True) == pytest.approx(min(1920 / 908, 1040 / 458, SCALE_MAX))


def test_clamp_scale_limits():
    assert clamp_scale(0.01, 1.2) == SCALE_MIN
    assert clamp_scale(5, 1.2) == 1.2


def test_anchor_left_edge_keeps_right_side():
    pos = anchored_pos("left", QRectF(100, 100, 400, 800), QSizeF(300, 600))
    assert (pos.x(), pos.y()) == (200, 100)


def test_anchor_topleft_keeps_bottom_right():
    pos = anchored_pos("topleft", QRectF(100, 100, 400, 800), QSizeF(300, 600))
    assert (pos.x(), pos.y()) == (200, 300)


# --- окно целиком -----------------------------------------------------------
@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance()


def test_window_drag_bottom_right_corner_resizes(qapp):
    from PySide6.QtTest import QTest

    from app.main_window import MirrorWindow
    win = MirrorWindow(AppConfig(scale=0.6), lambda: [])
    win.show()
    changes = []
    win.config_changed.connect(changes.append)
    before = win.size()
    body = win.view.body_rect()
    corner = QPoint(int(body.right()) - 2, int(body.bottom()) - 2)
    QTest.mousePress(win.view, Qt.LeftButton, Qt.NoModifier, corner)
    QTest.mouseMove(win.view, corner + QPoint(60, 120))
    QTest.mouseRelease(win.view, Qt.LeftButton, Qt.NoModifier, corner + QPoint(60, 120))
    assert win.size().height() > before.height()
    assert changes and changes[-1].scale > 0.6
    win.close()


def test_window_set_scale_persists_and_clamps(qapp):
    from app.main_window import MirrorWindow
    win = MirrorWindow(AppConfig(scale=0.6), lambda: [])
    changes = []
    win.config_changed.connect(changes.append)
    win.set_scale(0.01)
    assert changes[-1].scale == SCALE_MIN
    win.close()
