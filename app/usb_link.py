# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Определение прямого подключения к iPhone (USB-кабель или Wi‑Fi-точка iPhone).

В «Режиме модема» iPhone всегда раздаёт подсеть 172.20.10.0/28 и сам имеет адрес
172.20.10.1. Если у ПК есть адрес в этой подсети — iPhone подключён напрямую,
и AirPlay пойдёт по этому каналу (без роутера). Тип интерфейса Ethernet означает
USB-кабель (драйвер «Apple Mobile Device Ethernet»), Wifi — точку доступа iPhone.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QAbstractSocket, QNetworkInterface

HOTSPOT_NET = ipaddress.ip_network("172.20.10.0/28")
POLL_MS = 2000


@dataclass(frozen=True)
class IfaceInfo:
    name: str
    kind: str            # "ethernet" | "wifi" | "other"
    up: bool
    ipv4: tuple[str, ...]


@dataclass(frozen=True)
class DirectLink:
    kind: str            # "usb" | "hotspot"
    interface: str
    pc_ip: str


def find_direct_link(interfaces: list[IfaceInfo]) -> DirectLink | None:
    """Чистая функция: ищет интерфейс в подсети «Режима модема» iPhone. USB важнее Wi‑Fi."""
    found: list[DirectLink] = []
    for iface in interfaces:
        if not iface.up:
            continue
        for ip in iface.ipv4:
            try:
                in_net = ipaddress.ip_address(ip) in HOTSPOT_NET
            except ValueError:
                continue
            if in_net:
                kind = "hotspot" if iface.kind == "wifi" else "usb"
                found.append(DirectLink(kind, iface.name, ip))
    found.sort(key=lambda link: link.kind != "usb")
    return found[0] if found else None


def _kind(iface: QNetworkInterface) -> str:
    t = iface.type()
    if t == QNetworkInterface.InterfaceType.Ethernet:
        return "ethernet"
    if t in (QNetworkInterface.InterfaceType.Wifi, QNetworkInterface.InterfaceType.Ieee80211):
        return "wifi"
    return "other"


def system_interfaces() -> list[IfaceInfo]:
    result = []
    for iface in QNetworkInterface.allInterfaces():
        flags = iface.flags()
        up = bool(flags & QNetworkInterface.InterfaceFlag.IsUp) and bool(flags & QNetworkInterface.InterfaceFlag.IsRunning)
        ips = tuple(e.ip().toString() for e in iface.addressEntries()
                    if e.ip().protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol)
        result.append(IfaceInfo(iface.humanReadableName(), _kind(iface), up, ips))
    return result


class LinkMonitor(QObject):
    """Периодически проверяет сетевые интерфейсы и сообщает о смене прямого подключения."""

    link_changed = Signal(object)   # DirectLink | None

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._link: DirectLink | None = None
        self._timer = QTimer(self, interval=POLL_MS, timeout=self.check)

    @property
    def link(self) -> DirectLink | None:
        return self._link

    def start(self) -> None:
        self.check()
        self._timer.start()

    def check(self) -> None:
        link = find_direct_link(system_interfaces())
        if link != self._link:
            self._link = link
            self.link_changed.emit(link)
