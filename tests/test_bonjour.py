# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Тесты выбора варианта UxPlay (Bonjour / встроенный mDNS)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.bonjour import BONJOUR_VARIANT, choose_variant, is_bonjour_running
from app.config import AppConfig


@pytest.fixture()
def both(tmp_path: Path) -> Path:
    base = tmp_path / "uxplay.exe"
    base.write_bytes(b"")
    (tmp_path / BONJOUR_VARIANT).write_bytes(b"")
    return base


def test_auto_uses_bonjour_when_service_runs(both):
    exe, _ = choose_variant(both, "auto", bonjour_running=True)
    assert exe.name == BONJOUR_VARIANT


def test_auto_uses_internal_without_service(both):
    exe, _ = choose_variant(both, "auto", bonjour_running=False)
    assert exe == both


def test_internal_mode_ignores_bonjour(both):
    exe, _ = choose_variant(both, "internal", bonjour_running=True)
    assert exe == both


def test_bonjour_mode_falls_back_when_variant_missing(tmp_path):
    base = tmp_path / "uxplay.exe"
    base.write_bytes(b"")
    exe, how = choose_variant(base, "bonjour", bonjour_running=True)
    assert exe == base and "не найден" in how


def test_config_rejects_unknown_mdns_mode():
    assert AppConfig().with_changes(mdns_mode="magic").mdns_mode == "auto"


def test_is_bonjour_running_returns_bool():
    assert isinstance(is_bonjour_running(), bool)
