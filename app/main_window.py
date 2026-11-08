# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Безрамочное окно-«айфон»: перетаскивание, масштаб (края, колесо, клавиши), меню."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, QSizeF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QVBoxLayout, QWidget

from .common_actions import CommonActions
from .config import COLORS, AppConfig
from .phone_view import PhoneView
from .scaling import (PRESETS_PERCENT, anchored_pos, clamp_scale, edge_at, max_scale_for,
                      scale_from_drag)

COLOR_NAMES = {"natural": "Натуральный титан", "black": "Чёрный титан",
               "white": "Белый титан", "blue": "Синий титан"}
SCALE_STEP = 0.05
TOAST_MS = 900
EDGE_CURSORS = {
    "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
    "top": Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor,
    "topleft": Qt.SizeFDiagCursor, "bottomright": Qt.SizeFDiagCursor,
    "topright": Qt.SizeBDiagCursor, "bottomleft": Qt.SizeBDiagCursor,
}


class MirrorWindow(QWidget, CommonActions):
    config_changed = Signal(object)       # AppConfig
    restart_requested = Signal()
    mode_requested = Signal(str)          # "phone" | "window"

    def __init__(self, cfg: AppConfig, log_provider) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.Window)
        self._cfg = cfg
        self._log_provider = log_provider
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(f"iPhone Mirror — {cfg.device_name}")
        self.view = PhoneView(cfg.scale, cfg.model_color, cfg.device_name, self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)
        self._drag: tuple[str, QPointF, float, QSizeF, QRectF] | None = None
        self.setMouseTracking(True)
        self._toast = QLabel(self)
        self._toast.setAlignment(Qt.AlignCenter)
        self._toast.setStyleSheet("background: rgba(0,0,0,170); color: white; border-radius: 12px;"
                                  "padding: 6px 14px; font: 600 15px 'Segoe UI';")
        self._toast.hide()
        self._toast_timer = QTimer(self, singleShot=True, interval=TOAST_MS, timeout=self._toast.hide)
        self._apply_on_top(cfg.always_on_top)
        self._place_initially()
        self.refit()
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_screenshot)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=QApplication.quit)
        for keys in ("Ctrl+=", "Ctrl++"):
            QShortcut(QKeySequence(keys), self, activated=lambda: self.set_scale(self.view.scale + SCALE_STEP))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self.set_scale(self.view.scale - SCALE_STEP))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=lambda: self.set_scale(AppConfig.scale))

    # --- показ трансляции (общий интерфейс с обычным окном) -------------------
    @property
    def screenshot_image(self) -> QImage | None:
        return self.view.current_image

    @property
    def is_streaming(self) -> bool:
        return self.view.current_image is not None

    def show_frame(self, image: QImage) -> None:
        was_landscape = self.view.landscape
        self.view.show_frame(image)
        if self.view.landscape != was_landscape:
            self.refit()

    def set_streaming(self, active: bool) -> None:
        self.view.set_streaming(active)
        self.refit()

    def set_status(self, status: str) -> None:
        self.view.set_status(status)

    def set_link(self, link) -> None:
        self._link = link
        self.view.set_link(link.kind if link else None)

    def on_device_name_changed(self, name: str) -> None:
        self.view.set_device_name(name)

    def save_geometry(self) -> None:
        pos = self.pos()
        self._update_config(window_x=pos.x(), window_y=pos.y())

    # --- положение и размер -------------------------------------------------
    def _place_initially(self) -> None:
        self.adjustSize()
        if self._cfg.window_x >= 0 and self._cfg.window_y >= 0:
            pos = QPoint(self._cfg.window_x, self._cfg.window_y)
            if QGuiApplication.screenAt(pos + QPoint(40, 40)) is not None:
                self.move(pos)
                return
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.center() - self.rect().center())

    def _max_scale(self) -> float:
        screen = self.screen() or QGuiApplication.primaryScreen()
        return max_scale_for(QSizeF(screen.availableGeometry().size()), self.view.landscape)

    def refit(self) -> None:
        """Подгоняет окно под виджет, сохраняя центр (например, при повороте).
        Если после поворота телефон не помещается на экран — уменьшает его."""
        limit = self._max_scale()
        if self.view.scale > limit:
            self.view.set_scale(limit)
        center = self.frameGeometry().center()
        self.adjustSize()
        self.resize(self.view.size())
        self.move(center - self.rect().center())

    def set_scale(self, scale: float, edge: str = "", start_geom: QRectF | None = None,
                  persist: bool = True) -> None:
        """Меняет масштаб. С `edge` — держит противоположный край окна на месте."""
        scale = clamp_scale(scale, self._max_scale())
        if abs(scale - self.view.scale) >= 1e-3:
            self.view.set_scale(scale)
            if edge and start_geom is not None:
                self.adjustSize()
                self.resize(self.view.size())
                self.move(anchored_pos(edge, start_geom, QSizeF(self.view.size())).toPoint())
            else:
                self.refit()
        self._show_toast(f"{round(self.view.scale * 100)}%")
        if persist:
            self._update_config(scale=self.view.scale)

    def fit_screen_height(self) -> None:
        self.set_scale(self._max_scale())

    def _show_toast(self, text: str) -> None:
        self._toast.setText(text)
        self._toast.adjustSize()
        body = self.view.body_rect()
        self._toast.move(int(body.center().x() - self._toast.width() / 2),
                         int(body.center().y() - self._toast.height() / 2))
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start()

    def _apply_on_top(self, on: bool) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)

    # --- события мыши -------------------------------------------------------
    def _edge_under(self, pos: QPointF) -> str:
        return edge_at(pos, self.view.body_rect())

    def mousePressEvent(self, e) -> None:
        if e.button() != Qt.LeftButton:
            return
        edge = self._edge_under(e.position())
        if edge:   # тянем за край — меняем масштаб
            self._drag = (edge, e.globalPosition(), self.view.scale,
                          QSizeF(self.size()), QRectF(self.geometry()))
        elif self.windowHandle():
            self.windowHandle().startSystemMove()

    def mouseMoveEvent(self, e) -> None:
        if self._drag is None:
            edge = self._edge_under(e.position())
            if edge:
                self.view.setCursor(EDGE_CURSORS[edge])
            else:
                self.view.unsetCursor()
            return
        edge, start, start_scale, start_size, start_geom = self._drag
        delta = e.globalPosition() - start
        scale = scale_from_drag(edge, start_scale, start_size, delta.x(), delta.y())
        self.set_scale(scale, edge=edge, start_geom=start_geom, persist=False)

    def mouseReleaseEvent(self, _e) -> None:
        if self._drag is not None:
            self._drag = None
            self._update_config(scale=self.view.scale)

    def wheelEvent(self, e) -> None:
        if e.modifiers() & Qt.ControlModifier:
            step = SCALE_STEP if e.angleDelta().y() > 0 else -SCALE_STEP
            self.set_scale(self.view.scale + step)

    def mouseDoubleClickEvent(self, _e) -> None:
        self.showMinimized()

    def contextMenuEvent(self, e) -> None:
        self._build_menu().exec(e.globalPos())

    # --- меню ---------------------------------------------------------------
    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        on_top = QAction("Поверх всех окон", menu, checkable=True, checked=self._cfg.always_on_top)
        on_top.toggled.connect(self._toggle_on_top)
        menu.addAction(on_top)

        current = round(self.view.scale * 100)
        size_menu = menu.addMenu(f"Масштаб: {current}%")
        group_size = QActionGroup(size_menu)
        for pct in PRESETS_PERCENT:
            act = QAction(f"{pct}%", size_menu, checkable=True, checked=pct == current)
            act.triggered.connect(lambda _=False, v=pct / 100: self.set_scale(v))
            group_size.addAction(act)
            size_menu.addAction(act)
        size_menu.addAction("По высоте экрана", self.fit_screen_height)
        size_menu.addSeparator()
        size_menu.addAction("Крупнее  (Ctrl +)", lambda: self.set_scale(self.view.scale + SCALE_STEP))
        size_menu.addAction("Мельче  (Ctrl −)", lambda: self.set_scale(self.view.scale - SCALE_STEP))
        size_menu.addAction("По умолчанию  (Ctrl 0)", lambda: self.set_scale(AppConfig.scale))
        hint = size_menu.addAction("Тяните за край телефона или Ctrl + колесо")
        hint.setEnabled(False)

        color_menu = menu.addMenu("Цвет корпуса")
        group = QActionGroup(color_menu)
        for key in COLORS:
            act = QAction(COLOR_NAMES[key], color_menu, checkable=True, checked=key == self._cfg.model_color)
            act.triggered.connect(lambda _=False, k=key: self._set_color(k))
            group.addAction(act)
            color_menu.addAction(act)

        self.add_common_menu(menu)
        menu.insertAction(menu.actions()[-1], QAction("Свернуть  (двойной клик)", menu,
                                                      triggered=self.showMinimized))
        return menu

    def _toggle_on_top(self, on: bool) -> None:
        self._apply_on_top(on)
        self.show()
        self._update_config(always_on_top=on)

    def _set_color(self, key: str) -> None:
        self.view.set_color(key)
        self._update_config(model_color=key)
