# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Рисует картинки для README (docs/images/*) тем же кодом, что и приложение."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.about_dialog import AboutDialog  # noqa: E402
from app.lock_screen import paint_wallpaper  # noqa: E402
from app.phone_view import PhoneView  # noqa: E402

OUT = ROOT / "docs" / "images"
BG_TOP, BG_BOTTOM, GLOW = QColor("#0f0a1c"), QColor("#1c1233"), QColor(124, 58, 237, 120)


def brand_background(w: int, h: int) -> QImage:
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, h)
    grad.setColorAt(0, BG_TOP)
    grad.setColorAt(1, BG_BOTTOM)
    p.fillRect(img.rect(), grad)
    glow = QRadialGradient(QPointF(w / 2, h * 0.55), w * 0.45)
    glow.setColorAt(0, GLOW)
    glow.setColorAt(1, QColor(0, 0, 0, 0))
    p.fillRect(img.rect(), glow)
    p.end()
    return img


def phone_image(scale: float, color: str, link: str | None = None, frame: QImage | None = None) -> QImage:
    view = PhoneView(scale, color, "iPhone Mirror PC")
    view.set_link(link)
    if frame is not None:
        view.show_frame(frame)
    return view.grab().toImage()


def wallpaper_frame(w: int, h: int) -> QImage:
    img = QImage(w, h, QImage.Format_RGB888)
    p = QPainter(img)
    paint_wallpaper(p, QRectF(0, 0, w, h))
    p.end()
    return img


def compose(bg: QImage, items: list[tuple[QImage, float, float]]) -> QImage:
    p = QPainter(bg)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    for img, cx, cy in items:
        p.drawImage(QPointF(cx - img.width() / 2, cy - img.height() / 2), img)
    p.end()
    return bg


def save(img: QImage, name: str) -> None:
    path = OUT / name
    if not img.save(str(path)):
        raise SystemExit(f"не удалось сохранить {path}")
    print(name, img.width(), "x", img.height())


def main() -> None:
    app = QApplication.instance() or QApplication([])
    OUT.mkdir(parents=True, exist_ok=True)

    # Главная: четыре цвета корпуса.
    phones = [phone_image(0.62, c) for c in ("black", "natural", "blue", "white")]
    w, h = 1600, 760
    step = 330
    x0 = w / 2 - step * 1.5
    save(compose(brand_background(w, h), [(img, x0 + i * step, h / 2) for i, img in enumerate(phones)]),
         "hero.png")

    # Горизонтальный режим (окно само поворачивается вместе с iPhone).
    land = phone_image(0.75, "natural", frame=wallpaper_frame(1920, 886))
    save(compose(brand_background(980, 560), [(land, 490, 280)]), "landscape.png")

    # Подключение по кабелю: плашка USB.
    usb = phone_image(0.62, "blue", link="usb")
    save(compose(brand_background(560, 680), [(usb, 280, 340)]), "usb.png")

    # Режим «обычное окно» с панелью инструментов (горизонтальная картинка).
    from app.config import AppConfig
    from app.plain_window import PlainWindow
    plain = PlainWindow(AppConfig(view_mode="window", plain_x=50, plain_y=50, plain_w=1000, plain_h=480),
                        lambda: [])
    plain.show()
    plain.show_frame(wallpaper_frame(1920, 886))
    plain.fit_window_to_picture()
    app.processEvents()
    save(plain.grab().toImage(), "window-mode.png")
    plain.close()

    # О программе.
    about = AboutDialog()
    about.show()
    app.processEvents()
    save(about.grab().toImage(), "about.png")
    about.close()


if __name__ == "__main__":
    main()
