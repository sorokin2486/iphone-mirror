"""Выбор способа объявления ПК в сети: системный Bonjour или встроенный mDNS UxPlay.

Встроенный mDNS UxPlay отправляет объявления по маршруту multicast по умолчанию.
При VPN в режиме TUN (sing-box, MantaRay и т.п.) этот маршрут ведёт в туннель, и iPhone
не видит ПК ни по Wi‑Fi, ни по кабелю. Кроме того, запущенная служба Bonjour
(mDNSResponder) сама слушает порт 5353 и забирает входящие mDNS-запросы.
Поэтому, если Bonjour работает, используем вариант UxPlay, собранный с ним
(uxplay-bonjour.exe): Bonjour объявляет службу на всех сетевых интерфейсах.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

BONJOUR_SERVICE = "Bonjour Service"
BONJOUR_VARIANT = "uxplay-bonjour.exe"
SC_TIMEOUT_S = 5


def is_bonjour_running() -> bool:
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(
            ["sc", "query", BONJOUR_SERVICE], capture_output=True, text=True,
            timeout=SC_TIMEOUT_S, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("Не удалось проверить службу Bonjour: %s", exc)
        return False
    return "RUNNING" in out


def choose_variant(base: Path, mode: str, bonjour_running: bool) -> tuple[Path, str]:
    """Возвращает (exe, описание). Чистая функция — для тестов.

    mode: "auto" — Bonjour, если служба запущена и вариант есть; иначе встроенный mDNS;
          "bonjour" — Bonjour, если вариант есть (иначе встроенный);
          "internal" — всегда встроенный mDNS.
    """
    bonjour_exe = base.with_name(BONJOUR_VARIANT)
    want_bonjour = mode == "bonjour" or (mode == "auto" and bonjour_running)
    if want_bonjour and bonjour_exe.is_file():
        return bonjour_exe, "Bonjour (все сетевые интерфейсы)"
    if want_bonjour:
        return base, "встроенный mDNS (вариант с Bonjour не найден)"
    return base, "встроенный mDNS"
