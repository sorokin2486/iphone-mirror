# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Обычное окно Windows (без картинки iPhone) с панелью инструментов, как в ApowerMirror:
поворот, зеркало, вписать/растянуть/заполнить, полный экран, поверх окон, скриншот."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, QSizeF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QFont, QGuiApplication, QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMenu, QToolButton, QVBoxLayout,
                               QWidget)

from .common_actions import CommonActions
from .config import AppConfig
from .plain_view import PlainView

TOOLBAR_W = 52
TOAST_MS = 1200
ICON_FONT = "Segoe Fluent Icons"
FIT_INFO = {   # режим: (иконка, подпись)
    "fit": ("", "Вписать (с сохранением пропорций)"),
    "stretch": ("", "Растянуть на всё окно"),
    "fill": ("", "Заполнить (с обрезкой краёв)"),
}
GLYPH = {
    "rotate_left": "", "rotate_right": "", "mirror": "",
    "fullscreen": "", "pin": "", "unpin": "", "shot": "",
    "folder": "", "fit_window": "", "phone": "", "more": "",
}
STYLE = """
QWidget#plainRoot { background: #0e0d12; }
QWidget#toolbar { background: #17151f; border-left: 1px solid #262233; }
QToolButton { color: #d9d3ea; background: transparent; border: none; border-radius: 8px;
              min-width: 38px; min-height: 38px; }
QToolButton:hover { background: #2a2540; }
QToolButton:checked { background: #7c3aed; color: white; }
QToolButton::menu-indicator { image: none; }
QLabel#toast { background: rgba(0,0,0,180); color: white; border-radius: 12px;
               padding: 8px 16px; font: 600 14px 'Segoe UI'; }
"""


def window_size_for(content: QSizeF, video_height: float, chrome_w: float, available: QSizeF) -> QSize:
    """Размер клиентской области окна, при котором видео точно под пропорции картинки."""
    if content.isEmpty():
        return QSize(int(chrome_w + video_height * 0.5), int(video_height))
    ratio = content.width() / content.height()
    h = min(video_height, available.height())
    w = h * ratio
    if w + chrome_w > available.width():
        w = available.width() - chrome_w
        h = w / ratio
    return QSize(round(w + chrome_w), round(h))


class PlainWindow(QWidget, CommonActions):
    config_changed = Signal(object)
    restart_requested = Signal()
    mode_requested = Signal(str)

    def __init__(self, cfg: AppConfig, log_provider) -> None:
        super().__init__(None, Qt.Window)
        self._cfg = cfg
        self._log_provider = log_provider
        self._last_aspect: QSizeF | None = None
        self.setObjectName("plainRoot")
        self.setStyleSheet(STYLE)
        self.setWindowTitle(f"iPhone Mirror — {cfg.device_name}")
        self.setMinimumSize(240, 240)

        self.view = PlainView(cfg.device_name, cfg.fit_mode, cfg.rotation, cfg.mirrored, self)
        self.view.double_clicked.connect(self.toggle_fullscreen)
        self.view.menu_requested.connect(lambda pos: self._build_menu().exec(pos))
        self.toolbar = self._build_toolbar()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.view, 1)
        lay.addWidget(self.toolbar)

        self._toast = QLabel(self, objectName="toast", alignment=Qt.AlignCenter)
        self._toast.hide()
        self._toast_timer = QTimer(self, singleShot=True, interval=TOAST_MS, timeout=self._toast.hide)
        self._apply_on_top(cfg.always_on_top, show=False)
        self._restore_geometry()
        self._bind_keys()

    # --- общий интерфейс показа -----------------------------------------------
    @property
    def screenshot_image(self) -> QImage | None:
        return self.view.displayed_image()

    @property
    def is_streaming(self) -> bool:
        return self.view.current_image is not None

    def show_frame(self, image: QImage) -> None:
        self.view.show_frame(image)
        self._follow_aspect()

    def set_streaming(self, active: bool) -> None:
        self.view.set_streaming(active)
        self._follow_aspect()

    def set_status(self, status: str) -> None:
        self.view.set_status(status)

    def set_link(self, link) -> None:
        self._link = link
        self.view.set_link(link.kind if link else None)

    def on_device_name_changed(self, name: str) -> None:
        self.view.set_device_name(name)

    def save_geometry(self) -> None:
        g = self.normalGeometry() if (self.isMaximized() or self.isFullScreen()) else self.geometry()
        self._update_config(plain_x=g.x(), plain_y=g.y(), plain_w=g.width(), plain_h=g.height())

    # --- панель инструментов ------------------------------------------------
    def _button(self, glyph: str, tip: str, slot=None, checkable: bool = False) -> QToolButton:
        b = QToolButton(self, text=glyph, toolTip=tip, checkable=checkable, autoRaise=True)
        b.setFont(QFont(ICON_FONT, 13))
        b.setCursor(Qt.PointingHandCursor)
        if slot is not None:
            (b.toggled if checkable else b.clicked).connect(slot)
        return b

    def _build_toolbar(self) -> QWidget:
        bar = QWidget(self, objectName="toolbar")
        bar.setFixedWidth(TOOLBAR_W)
        col = QVBoxLayout(bar)
        col.setContentsMargins(7, 10, 7, 10)
        col.setSpacing(4)
        self.btn_on_top = self._button(GLYPH["pin"], "Поверх всех окон", self._set_on_top, checkable=True)
        self.btn_mirror = self._button(GLYPH["mirror"], "Зеркально  (Ctrl+M)", self._set_mirror, checkable=True)
        for btn, on in ((self.btn_on_top, self._cfg.always_on_top), (self.btn_mirror, self._cfg.mirrored)):
            btn.blockSignals(True)      # начальное состояние — без побочных действий
            btn.setChecked(on)
            btn.blockSignals(False)
        self.btn_on_top.setText(GLYPH["unpin"] if self._cfg.always_on_top else GLYPH["pin"])
        self.btn_fit = self._button(FIT_INFO[self._cfg.fit_mode][0], "Режим картинки")
        self.btn_fit.setPopupMode(QToolButton.InstantPopup)
        self.btn_fit.setMenu(self._fit_menu(self.btn_fit))
        widgets = [
            self._button(GLYPH["fullscreen"], "Полный экран  (F11, двойной клик)", self.toggle_fullscreen),
            self.btn_on_top,
            None,
            self._button(GLYPH["rotate_left"], "Повернуть влево  (Ctrl+Shift+R)", lambda: self.rotate(-1)),
            self._button(GLYPH["rotate_right"], "Повернуть вправо  (Ctrl+R)", lambda: self.rotate(1)),
            self.btn_mirror,
            self.btn_fit,
            self._button(GLYPH["fit_window"], "Подогнать окно под картинку", self.fit_window_to_picture),
            None,
            self._button(GLYPH["shot"], "Скриншот  (Ctrl+S)", self.save_screenshot),
            self._button(GLYPH["folder"], "Папка скриншотов", self.open_screenshot_dir),
        ]
        for w in widgets:
            if w is None:
                col.addSpacing(10)
            else:
                col.addWidget(w, alignment=Qt.AlignHCenter)
        col.addStretch(1)
        col.addWidget(self._button(GLYPH["phone"], "Вид «iPhone»", lambda: self.mode_requested.emit("phone")),
                      alignment=Qt.AlignHCenter)
        more = self._button(GLYPH["more"], "Ещё")
        more.setPopupMode(QToolButton.InstantPopup)
        more.clicked.connect(lambda: self._build_menu().exec(more.mapToGlobal(QPoint(0, more.height()))))
        col.addWidget(more, alignment=Qt.AlignHCenter)
        return bar

    def _fit_menu(self, parent) -> QMenu:
        menu = QMenu(parent)
        group = QActionGroup(menu)
        for key, (_glyph, title) in FIT_INFO.items():
            act = QAction(title, menu, checkable=True, checked=key == self._cfg.fit_mode)
            act.triggered.connect(lambda _=False, k=key: self.set_fit_mode(k))
            group.addAction(act)
            menu.addAction(act)
        return menu

    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("Полный экран  (F11)", self.toggle_fullscreen)
        on_top = QAction("Поверх всех окон", menu, checkable=True, checked=self._cfg.always_on_top)
        on_top.toggled.connect(self._set_on_top)
        menu.addAction(on_top)
        menu.addSeparator()
        menu.addAction("Повернуть вправо  (Ctrl+R)", lambda: self.rotate(1))
        menu.addAction("Повернуть влево  (Ctrl+Shift+R)", lambda: self.rotate(-1))
        mirror = QAction("Зеркально  (Ctrl+M)", menu, checkable=True, checked=self._cfg.mirrored)
        mirror.toggled.connect(self._set_mirror)
        menu.addAction(mirror)
        menu.addMenu(self._fit_menu(menu)).setText("Картинка")
        menu.addAction("Подогнать окно под картинку", self.fit_window_to_picture)
        menu.addAction("Сбросить поворот и зеркало", self.reset_transform)
        self.add_common_menu(menu)
        return menu

    def _bind_keys(self) -> None:
        keys = {
            "Ctrl+S": self.save_screenshot, "Ctrl+Q": QApplication.quit, "F11": self.toggle_fullscreen,
            "Esc": self._exit_fullscreen, "Ctrl+R": lambda: self.rotate(1),
            "Ctrl+Shift+R": lambda: self.rotate(-1), "Ctrl+M": lambda: self.btn_mirror.toggle(),
        }
        for seq, slot in keys.items():
            QShortcut(QKeySequence(seq), self, activated=slot)

    # --- инструменты --------------------------------------------------------
    def rotate(self, step: int) -> None:
        self._update_config(rotation=(self._cfg.rotation + step) % 4)
        self._apply_transform()
        self._show_toast(f"Поворот {self._cfg.rotation * 90}°")

    def _set_mirror(self, on: bool) -> None:
        if self.btn_mirror.isChecked() != on:
            self.btn_mirror.setChecked(on)     # синхронизация с пунктом меню
            return
        self._update_config(mirrored=on)
        self._apply_transform()

    def set_fit_mode(self, mode: str) -> None:
        self._update_config(fit_mode=mode)
        self.btn_fit.setText(FIT_INFO[self._cfg.fit_mode][0])
        self.btn_fit.setMenu(self._fit_menu(self.btn_fit))
        self._apply_transform()
        self._show_toast(FIT_INFO[self._cfg.fit_mode][1])

    def reset_transform(self) -> None:
        self.btn_mirror.setChecked(False)
        self._update_config(rotation=0, mirrored=False)
        self._apply_transform()

    def _apply_transform(self) -> None:
        self.view.set_transform(self._cfg.fit_mode, self._cfg.rotation, self._cfg.mirrored)
        self._follow_aspect()

    def _set_on_top(self, on: bool) -> None:
        if self.btn_on_top.isChecked() != on:
            self.btn_on_top.setChecked(on)
            return
        self.btn_on_top.setText(GLYPH["unpin"] if on else GLYPH["pin"])
        self._apply_on_top(on)
        self._update_config(always_on_top=on)

    def _apply_on_top(self, on: bool, show: bool = True) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        if show:
            self.show()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self._exit_fullscreen()
            return
        self.toolbar.hide()
        self.showFullScreen()
        self._show_toast("Полный экран — Esc или двойной клик, чтобы выйти")

    def _exit_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.show()

    # --- размер окна под картинку -------------------------------------------
    def _available_client(self) -> QSizeF:
        screen = self.screen() or QGuiApplication.primaryScreen()
        frame_extra = self.frameGeometry().size() - self.geometry().size()
        avail = screen.availableGeometry().size() - frame_extra
        return QSizeF(avail.width(), avail.height())

    def fit_window_to_picture(self) -> None:
        if self.isFullScreen() or self.isMaximized():
            self.showNormal()
            self.toolbar.show()
        size = window_size_for(self.view.content_aspect(), self.view.height(), TOOLBAR_W,
                               self._available_client())
        center = self.geometry().center()
        self.resize(size)
        g = self.geometry()
        g.moveCenter(center)
        self.setGeometry(self._clamp_to_screen(g))

    def _follow_aspect(self) -> None:
        """Когда меняется ориентация картинки (поворот iPhone, кнопка «повернуть»),
        подгоняем окно, чтобы не было больших чёрных полей. Только в обычном состоянии окна."""
        aspect = self.view.content_aspect()
        landscape = aspect.width() > aspect.height()
        prev = self._last_aspect
        self._last_aspect = aspect
        if prev is None or (prev.width() > prev.height()) == landscape:
            return
        if not (self.isFullScreen() or self.isMaximized()) and self.isVisible():
            self.fit_window_to_picture()

    def _clamp_to_screen(self, g: QRect) -> QRect:
        screen = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        g.moveLeft(max(screen.left(), min(g.left(), screen.right() - g.width())))
        g.moveTop(max(screen.top(), min(g.top(), screen.bottom() - g.height())))
        return g

    def _restore_geometry(self) -> None:
        c = self._cfg
        if min(c.plain_w, c.plain_h) >= 200:
            g = QRect(c.plain_x, c.plain_y, c.plain_w, c.plain_h)
            if QGuiApplication.screenAt(g.center()) is not None:
                self.setGeometry(g)
                return
        avail = self._available_client()
        size = window_size_for(self.view.content_aspect(), avail.height() * 0.8, TOOLBAR_W, avail)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(QRect(QPoint(screen.center().x() - size.width() // 2,
                                      screen.center().y() - size.height() // 2), size))

    def _show_toast(self, text: str) -> None:
        self._toast.setText(text)
        self._toast.adjustSize()
        area = self.view.geometry()
        self._toast.move(area.center().x() - self._toast.width() // 2, area.top() + 24)
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start()
