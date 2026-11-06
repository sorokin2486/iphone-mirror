"""Рисует иконку приложения (assets/icon.png + icon.ico) тем же кодом, что и окно."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app import phone_skin as skin  # noqa: E402
from app.lock_screen import paint_wallpaper  # noqa: E402

SIZE = 256


def render() -> QImage:
    img = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    scale = SIZE / (skin.BODY_H + 2 * skin.MARGIN)
    layout = skin.PhoneLayout.create(scale)
    p.translate((SIZE - layout.canvas.width()) / 2, 0)
    skin.paint_buttons(p, layout, scale, "natural")
    skin.paint_body(p, layout, scale, "natural")
    p.save()
    p.setClipPath(skin.screen_path(layout, scale))
    paint_wallpaper(p, layout.screen)
    # Значок «повтор экрана»: два перекрывающихся прямоугольника.
    c = layout.screen.center()
    w = layout.screen.width() * 0.5
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 120))
    p.drawRoundedRect(QRectF(c.x() - w * 0.55, c.y() - w * 0.45, w * 0.8, w * 0.65), w * 0.1, w * 0.1)
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawRoundedRect(QRectF(c.x() - w * 0.25, c.y() - w * 0.2, w * 0.8, w * 0.65), w * 0.1, w * 0.1)
    p.restore()
    skin.paint_island(p, layout, scale, active=False)
    p.end()
    return img


if __name__ == "__main__":
    app = QApplication([])
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    image = render()
    for name in ("icon.png", "icon.ico"):
        if not image.save(str(out / name)):
            raise SystemExit(f"не удалось сохранить {name}")
    print("icon ->", out)
