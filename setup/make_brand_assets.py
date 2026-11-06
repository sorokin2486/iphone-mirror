# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Готовит фирменные картинки из исходного логотипа assets/sorokin-dev-logo.png:

  assets/logo-dark.png   — логотип, обрезанный по содержимому (для тёмного фона);
  assets/logo-light.png  — то же, но надпись «sorokin» перекрашена в тёмный (для светлого фона);
  assets/badge-dev.png   — только фиолетовая плашка «dev» (для иконки приложения).
"""
import sys
from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "sorokin-dev-logo.png"
DARK_TEXT = QColor("#241b3a")
PAD = 16


def content_rect(img: QImage, x_from: int = 0, x_to: int | None = None, min_alpha: int = 8) -> QRect:
    x_to = img.width() if x_to is None else x_to
    xs, ys = [], []
    for y in range(img.height()):
        for x in range(x_from, x_to):
            if img.pixelColor(x, y).alpha() >= min_alpha:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise SystemExit("в логотипе нет непрозрачных пикселей")
    return QRect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def badge_left_edge(img: QImage) -> int:
    """Граница между надписью и плашкой: самый «пустой» столбец левее непрозрачной плашки."""
    solid = next((x for x in range(img.width()) for y in range(img.height())
                  if img.pixelColor(x, y).alpha() > 240 and img.pixelColor(x, y).red() < 170),
                 img.width() // 2)
    def column_alpha(x: int) -> int:
        return sum(img.pixelColor(x, y).alpha() for y in range(img.height()))
    window = range(max(0, solid - 70), solid)
    return min(window, key=column_alpha) if window else solid


def recolor_text(img: QImage, split_x: int) -> QImage:
    out = img.copy()
    for y in range(out.height()):
        for x in range(split_x):
            c = out.pixelColor(x, y)
            if c.alpha():
                out.setPixelColor(x, y, QColor(DARK_TEXT.red(), DARK_TEXT.green(), DARK_TEXT.blue(), c.alpha()))
    return out


def main() -> None:
    img = QImage(str(SRC)).convertToFormat(QImage.Format_ARGB32)
    if img.isNull():
        raise SystemExit(f"не удалось открыть {SRC}")
    split = badge_left_edge(img)
    whole = content_rect(img).adjusted(-PAD, -PAD, PAD, PAD).intersected(img.rect())
    badge = content_rect(img, x_from=split + 1, min_alpha=4).adjusted(-2, -4, 4, 4).intersected(img.rect())
    badge.setLeft(max(badge.left(), split + 1))

    outputs = {
        "logo-dark.png": img.copy(whole),
        "logo-light.png": recolor_text(img, split).copy(whole),
        "badge-dev.png": img.copy(badge),
    }
    for name, image in outputs.items():
        if not image.save(str(ROOT / "assets" / name)):
            raise SystemExit(f"не удалось сохранить {name}")
        print(name, image.width(), "x", image.height())


if __name__ == "__main__":
    sys.exit(main())
