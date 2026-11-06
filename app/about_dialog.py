# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Окно «О программе» с логотипом автора."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from . import __author__, __brand__, __copyright__, __url__, __version__
from .paths import LOGO_PATH

LOGO_WIDTH = 300


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setStyleSheet("QDialog { background: #120d1f; } QLabel { color: #e9e4f5; }"
                           "QPushButton { background: #7c3aed; color: white; border: none;"
                           " border-radius: 8px; padding: 6px 18px; font-weight: 600; }"
                           "QPushButton:hover { background: #8b5cf6; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(10)

        logo = QLabel(alignment=Qt.AlignCenter)
        pix = QPixmap(str(LOGO_PATH))
        if not pix.isNull():
            logo.setPixmap(pix.scaledToWidth(LOGO_WIDTH, Qt.SmoothTransformation))
        else:
            logo.setText(__brand__)
        lay.addWidget(logo)

        text = QLabel(
            f"<div style='text-align:center'>"
            f"<p style='font-size:18px; font-weight:600'>iPhone Mirror {__version__}</p>"
            f"<p>Экран и звук iPhone на Windows — по Wi‑Fi и по кабелю.</p>"
            f"<p>Автор: <b>{__author__}</b> ({__brand__})<br>{__copyright__}</p>"
            f"<p><a style='color:#a78bfa' href='{__url__}'>{__url__}</a></p>"
            f"<p style='color:#9b91b3; font-size:11px'>Лицензия GPL-3.0. Использует UxPlay, GStreamer, "
            f"FFmpeg, Qt.<br>AirPlay — торговая марка Apple Inc.</p></div>",
            alignment=Qt.AlignCenter, openExternalLinks=True, wordWrap=True)
        lay.addWidget(text)

        ok = QPushButton("Закрыть", clicked=self.accept)
        lay.addWidget(ok, alignment=Qt.AlignCenter)
