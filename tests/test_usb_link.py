"""Тесты определения прямого подключения к iPhone (USB / точка доступа)."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication

from app.usb_link import DirectLink, IfaceInfo, LinkMonitor, find_direct_link

LAN = IfaceInfo("Ethernet", "ethernet", True, ("192.168.1.20",))
USB = IfaceInfo("Ethernet 4", "ethernet", True, ("172.20.10.2",))
HOTSPOT = IfaceInfo("Wi-Fi", "wifi", True, ("172.20.10.3",))


def test_no_direct_link_on_regular_network():
    assert find_direct_link([LAN]) is None


def test_usb_tethering_detected_as_usb():
    assert find_direct_link([LAN, USB]) == DirectLink("usb", "Ethernet 4", "172.20.10.2")


def test_wifi_hotspot_detected_as_hotspot():
    assert find_direct_link([HOTSPOT]).kind == "hotspot"


def test_usb_preferred_over_hotspot():
    assert find_direct_link([HOTSPOT, USB]).kind == "usb"


def test_interface_down_is_ignored():
    down = IfaceInfo("Ethernet 4", "ethernet", False, ("172.20.10.2",))
    assert find_direct_link([down]) is None


def test_address_outside_hotspot_subnet_is_ignored():
    # 172.20.10.16 уже вне /28, который раздаёт iPhone.
    other = IfaceInfo("Ethernet 5", "ethernet", True, ("172.20.10.16", "not-an-ip"))
    assert find_direct_link([other]) is None


def test_monitor_emits_only_on_change(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    seq = iter([[LAN], [LAN], [LAN, USB], [LAN, USB], [LAN]])
    monkeypatch.setattr("app.usb_link.system_interfaces", lambda: next(seq))
    mon = LinkMonitor()
    events = []
    mon.link_changed.connect(events.append)
    for _ in range(5):
        mon.check()
    assert [e.kind if e else None for e in events] == ["usb", None]


@pytest.mark.parametrize("_", [0])
def test_system_interfaces_smoke(_):
    from app.usb_link import system_interfaces
    QCoreApplication.instance() or QCoreApplication([])
    assert isinstance(system_interfaces(), list)
