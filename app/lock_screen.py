"""Экран-заглушка в стиле экрана блокировки iOS, пока нет трансляции."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QRadialGradient

MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря")
WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")

STATUS_TEXT = {
    "running": "Откройте Пункт управления →\nПовтор экрана → «{name}»",
    "missing": "UxPlay не установлен.\nЗапустите setup\\install.ps1",
    "error": "Приёмник остановился.\nПКМ → «Перезапустить приёмник»",
    "stopped": "Приёмник выключен",
    "connecting": "Подключение…",
}


def _font(px: float, weight: QFont.Weight = QFont.Normal) -> QFont:
    f = QFont("Segoe UI Variable Display")
    f.setPixelSize(max(1, int(px)))
    f.setWeight(weight)
    return f


def paint_wallpaper(p: QPainter, rect: QRectF) -> None:
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#1b1f4b"))
    grad.setColorAt(0.5, QColor("#5b2a86"))
    grad.setColorAt(1.0, QColor("#e2647a"))
    p.fillRect(rect, grad)
    for cx, cy, r, col in ((0.2, 0.75, 0.7, QColor(255, 140, 90, 110)),
                           (0.85, 0.3, 0.6, QColor(70, 120, 255, 110))):
        rg = QRadialGradient(rect.left() + rect.width() * cx, rect.top() + rect.height() * cy,
                             rect.width() * r)
        rg.setColorAt(0, col)
        rg.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(rect, rg)


LINK_TEXT = {
    "usb": "Подключено по кабелю ✓\nПовтор экрана → «{name}»",
    "hotspot": "Через точку доступа iPhone ✓\nПовтор экрана → «{name}»",
}
LINK_BADGE = {"usb": "USB", "hotspot": "Hotspot"}


def paint_link_badge(p: QPainter, rect: QRectF, link_kind: str | None) -> None:
    """Плашка слева от Dynamic Island, как индикатор в строке состояния iOS."""
    if not link_kind:
        return
    w = rect.width()
    text = LINK_BADGE.get(link_kind, link_kind)
    p.setFont(_font(w * 0.036, QFont.DemiBold))
    tw = p.fontMetrics().horizontalAdvance(text)
    badge = QRectF(rect.left() + w * 0.08, rect.top() + w * 0.045, tw + w * 0.05, w * 0.06)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#30d158"))
    p.drawRoundedRect(badge, badge.height() / 2, badge.height() / 2)
    p.setPen(QColor("#ffffff"))
    p.drawText(badge, Qt.AlignCenter, text)


def paint_lock_screen(p: QPainter, rect: QRectF, status: str, device_name: str,
                      link_kind: str | None = None) -> None:
    paint_wallpaper(p, rect)
    paint_link_badge(p, rect, link_kind)
    now = datetime.now()
    w = rect.width()
    p.setPen(QColor(255, 255, 255, 235))

    date_rect = QRectF(rect.left(), rect.top() + rect.height() * 0.11, w, w * 0.07)
    p.setFont(_font(w * 0.05, QFont.DemiBold))
    p.drawText(date_rect, Qt.AlignCenter, f"{WEEKDAYS[now.weekday()]}, {now.day} {MONTHS[now.month - 1]}")

    time_rect = QRectF(rect.left(), date_rect.bottom(), w, w * 0.27)
    p.setFont(_font(w * 0.24, QFont.Bold))
    p.drawText(time_rect, Qt.AlignCenter, now.strftime("%H:%M"))

    template = STATUS_TEXT.get(status, STATUS_TEXT["running"])
    if status == "running" and link_kind in LINK_TEXT:
        template = LINK_TEXT[link_kind]
    text = template.format(name=device_name)
    card = QRectF(rect.left() + w * 0.08, rect.bottom() - rect.height() * 0.27, w * 0.84, rect.height() * 0.13)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 46))
    p.drawRoundedRect(card, w * 0.05, w * 0.05)
    p.setPen(QColor(255, 255, 255, 240))
    p.setFont(_font(w * 0.042, QFont.Medium))
    p.drawText(card.adjusted(w * 0.03, 0, -w * 0.03, 0), Qt.AlignCenter | Qt.TextWordWrap, text)

    # Полоска «домой» внизу.
    bar_w = w * 0.33
    bar = QRectF(rect.center().x() - bar_w / 2, rect.bottom() - w * 0.045, bar_w, w * 0.012)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 220))
    p.drawRoundedRect(bar, bar.height() / 2, bar.height() / 2)
