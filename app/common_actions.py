# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Действия, общие для обоих режимов окна: скриншот, звук, имя, USB, журнал, о программе.

Класс-примесь: окно должно иметь `_cfg`, `_log_provider`, сигналы `config_changed`,
`restart_requested`, `mode_requested` и свойство `screenshot_image`.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QDialog, QInputDialog, QMenu, QMessageBox,
                               QPlainTextEdit, QVBoxLayout)

from .about_dialog import AboutDialog

SCREENSHOT_DIR = Path.home() / "Pictures" / "iPhone Mirror"
USB_HELP = (
    "Трансляция по кабелю — без Wi‑Fi и роутера:\n\n"
    "1. На iPhone: Настройки → Режим модема → «Разрешать другим» — включить.\n"
    "2. Подключите iPhone к ПК кабелем, на iPhone нажмите «Доверять».\n"
    "3. Через несколько секунд в окне появится зелёная плашка «USB».\n"
    "4. Пункт управления → Повтор экрана → «{name}».\n\n"
    "Нужен драйвер Apple (приложение «Устройства Apple» из Microsoft Store или iTunes).\n"
    "Видео идёт напрямую по кабелю и не тратит мобильный трафик. Если Windows начнёт "
    "выходить в интернет через iPhone, отключите на iPhone мобильные данные.\n\n"
    "{state}"
)
MODE_NAMES = {"phone": "Режим: окно-«айфон»", "window": "Режим: обычное окно"}


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


class CommonActions:
    _link = None
    _log_dialog: LogDialog | None = None

    # --- настройки ----------------------------------------------------------
    def _update_config(self, **changes) -> None:
        self._cfg = self._cfg.with_changes(**changes)
        self.config_changed.emit(self._cfg)

    def on_device_name_changed(self, name: str) -> None:
        """Переопределяется окном, чтобы обновить подписи."""

    # --- общий раздел меню --------------------------------------------------
    def add_common_menu(self, menu: QMenu) -> None:
        mode = menu.addMenu("Вид окна")
        for key, title in MODE_NAMES.items():
            act = QAction(title, mode, checkable=True, checked=self._cfg.view_mode == key)
            act.triggered.connect(lambda _=False, k=key: self.mode_requested.emit(k))
            mode.addAction(act)
        menu.addSeparator()
        menu.addAction("Скриншот экрана  (Ctrl+S)", self.save_screenshot)
        menu.addAction("Открыть папку скриншотов", self.open_screenshot_dir)
        sound = QAction("Звук на ПК", menu, checkable=True, checked=self._cfg.audio_enabled)
        sound.toggled.connect(self._toggle_audio)
        menu.addAction(sound)
        menu.addAction("Имя приёмника…", self._rename)
        menu.addAction("Подключение по кабелю (USB)…", self.show_usb_help)
        menu.addSeparator()
        menu.addAction("Перезапустить приёмник", self.restart_requested.emit)
        menu.addAction("Журнал UxPlay", self.show_log)
        menu.addAction("О программе…", lambda: AboutDialog(self).exec())
        menu.addAction("Выход  (Ctrl+Q)", QApplication.quit)

    def _toggle_audio(self, on: bool) -> None:
        self._update_config(audio_enabled=on)
        self.restart_requested.emit()

    def _rename(self) -> None:
        name, ok = QInputDialog.getText(self, "Имя приёмника",
                                        "Как ПК будет называться в «Повторе экрана»:",
                                        text=self._cfg.device_name)
        if ok and name.strip():
            self._update_config(device_name=name)
            self.setWindowTitle(f"iPhone Mirror — {self._cfg.device_name}")
            self.on_device_name_changed(self._cfg.device_name)
            self.restart_requested.emit()

    # --- скриншоты ----------------------------------------------------------
    def save_screenshot(self) -> None:
        image = self.screenshot_image
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

    def open_screenshot_dir(self) -> None:
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(SCREENSHOT_DIR)  # noqa: S606 — открываем свою папку в Проводнике
        except OSError as exc:
            QMessageBox.warning(self, "Скриншоты", f"Не удалось открыть папку: {exc}")

    # --- USB и журнал -------------------------------------------------------
    def show_usb_help(self) -> None:
        link = self._link
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
        else:
            self._log_dialog.text.setPlainText("\n".join(self._log_provider()))
        self._log_dialog.show()
        self._log_dialog.raise_()

    def append_log(self, line: str) -> None:
        if self._log_dialog is not None:
            self._log_dialog.append(line)
