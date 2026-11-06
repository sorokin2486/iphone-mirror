"""Безрамочное окно-«айфон»: перетаскивание, масштаб колесом, контекстное меню."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QDialog, QInputDialog, QMenu, QMessageBox,
                               QPlainTextEdit, QVBoxLayout, QWidget)

from .config import COLORS, SCALE_MAX, SCALE_MIN, AppConfig
from .phone_view import PhoneView

SIZE_PRESETS = (("Маленький", 0.55), ("Средний", 0.8), ("Большой", 1.05))
COLOR_NAMES = {"natural": "Натуральный титан", "black": "Чёрный титан",
               "white": "Белый титан", "blue": "Синий титан"}
SCALE_STEP = 0.05
SCREENSHOT_DIR = Path.home() / "Pictures" / "iPhone Mirror"
USB_HELP = (
    "Трансляция по кабелю — без Wi‑Fi и роутера:\n\n"
    "1. На iPhone: Настройки → Режим модема → «Разрешать другим» — включить.\n"
    "2. Подключите iPhone к ПК кабелем, на iPhone нажмите «Доверять».\n"
    "3. Через несколько секунд на экране окна появится зелёная плашка «USB».\n"
    "4. Пункт управления → Повтор экрана → «{name}».\n\n"
    "Нужен драйвер Apple (приложение «Устройства Apple» из Microsoft Store или iTunes).\n"
    "Видео идёт напрямую по кабелю и не тратит мобильный трафик. Если Windows начнёт "
    "выходить в интернет через iPhone, отключите на iPhone мобильные данные.\n\n"
    "{state}"
)


class LogDialog(QDialog):
    def __init__(self, lines: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Журнал UxPlay")
        self.resize(760, 420)
        self.text = QPlainTextEdit(readOnly=True)
        self.text.setPlainText("\n".join(lines))
        lay = QVBoxLayout(self)
        lay.addWidget(self.text)

    def append(self, line: str) -> None:
        self.text.appendPlainText(line)


class MirrorWindow(QWidget):
    config_changed = Signal(object)       # AppConfig
    restart_requested = Signal()

    def __init__(self, cfg: AppConfig, log_provider) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.Window)
        self._cfg = cfg
        self._log_provider = log_provider
        self._log_dialog: LogDialog | None = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(f"iPhone Mirror — {cfg.device_name}")
        self.view = PhoneView(cfg.scale, cfg.model_color, cfg.device_name, self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)
        self._apply_on_top(cfg.always_on_top)
        self._place_initially()
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_screenshot)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=QApplication.quit)

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

    def refit(self) -> None:
        """Подгоняет окно под виджет, сохраняя центр (например, при повороте)."""
        center = self.frameGeometry().center()
        self.adjustSize()
        self.resize(self.view.size())
        self.move(center - self.rect().center())

    def _update_config(self, **changes) -> None:
        self._cfg = self._cfg.with_changes(**changes)
        self.config_changed.emit(self._cfg)

    def set_scale(self, scale: float) -> None:
        scale = min(max(scale, SCALE_MIN), SCALE_MAX)
        self.view.set_scale(scale)
        self.refit()
        self._update_config(scale=scale)

    def _apply_on_top(self, on: bool) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)

    # --- события мыши -------------------------------------------------------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self.windowHandle():
            self.windowHandle().startSystemMove()

    def wheelEvent(self, e) -> None:
        if e.modifiers() & Qt.ControlModifier:
            step = SCALE_STEP if e.angleDelta().y() > 0 else -SCALE_STEP
            self.set_scale(self._cfg.scale + step)

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

        size_menu = menu.addMenu("Размер")
        for name, value in SIZE_PRESETS:
            size_menu.addAction(name, lambda v=value: self.set_scale(v))
        size_menu.addSeparator()
        size_menu.addAction("Крупнее  (Ctrl + колесо)", lambda: self.set_scale(self._cfg.scale + SCALE_STEP))
        size_menu.addAction("Мельче", lambda: self.set_scale(self._cfg.scale - SCALE_STEP))

        color_menu = menu.addMenu("Цвет корпуса")
        group = QActionGroup(color_menu)
        for key in COLORS:
            act = QAction(COLOR_NAMES[key], color_menu, checkable=True, checked=key == self._cfg.model_color)
            act.triggered.connect(lambda _=False, k=key: self._set_color(k))
            group.addAction(act)
            color_menu.addAction(act)

        menu.addSeparator()
        menu.addAction("Скриншот экрана  (Ctrl+S)", self.save_screenshot)
        sound = QAction("Звук на ПК", menu, checkable=True, checked=self._cfg.audio_enabled)
        sound.toggled.connect(self._toggle_audio)
        menu.addAction(sound)
        menu.addAction("Имя приёмника…", self._rename)
        menu.addAction("Подключение по кабелю (USB)…", self.show_usb_help)
        menu.addSeparator()
        menu.addAction("Перезапустить приёмник", self.restart_requested.emit)
        menu.addAction("Журнал UxPlay", self.show_log)
        menu.addAction("Свернуть  (двойной клик)", self.showMinimized)
        menu.addAction("Выход  (Ctrl+Q)", QApplication.quit)
        return menu

    def _toggle_on_top(self, on: bool) -> None:
        self._apply_on_top(on)
        self.show()
        self._update_config(always_on_top=on)

    def _set_color(self, key: str) -> None:
        self.view.set_color(key)
        self._update_config(model_color=key)

    def _toggle_audio(self, on: bool) -> None:
        self._update_config(audio_enabled=on)
        self.restart_requested.emit()

    def _rename(self) -> None:
        name, ok = QInputDialog.getText(self, "Имя приёмника",
                                        "Как ПК будет называться в «Повторе экрана»:",
                                        text=self._cfg.device_name)
        if ok and name.strip():
            self._update_config(device_name=name)
            self.view.set_device_name(self._cfg.device_name)
            self.setWindowTitle(f"iPhone Mirror — {self._cfg.device_name}")
            self.restart_requested.emit()

    def save_screenshot(self) -> None:
        image = self.view.current_image
        if image is None:
            QMessageBox.information(self, "Скриншот", "Нет активной трансляции.")
            return
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Скриншот", f"Не удалось создать папку: {exc}")
            return
        path = SCREENSHOT_DIR / f"iPhone_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
        if image.save(str(path)):
            QMessageBox.information(self, "Скриншот", f"Сохранено:\n{path}")
        else:
            QMessageBox.warning(self, "Скриншот", "Не удалось сохранить файл.")

    def set_link(self, link) -> None:
        self._link = link
        self.view.set_link(link.kind if link else None)

    def show_usb_help(self) -> None:
        link = getattr(self, "_link", None)
        if link is None:
            state = "Сейчас: прямого подключения к iPhone нет."
        else:
            how = "по кабелю" if link.kind == "usb" else "через точку доступа iPhone"
            state = f"Сейчас: iPhone подключён {how} ({link.interface}, IP ПК {link.pc_ip})."
        QMessageBox.information(self, "Подключение по кабелю", USB_HELP.format(
            name=self._cfg.device_name, state=state))

    def show_log(self) -> None:
        if self._log_dialog is None:
            self._log_dialog = LogDialog(self._log_provider(), self)
        self._log_dialog.show()
        self._log_dialog.raise_()

    def append_log(self, line: str) -> None:
        if self._log_dialog is not None:
            self._log_dialog.append(line)
