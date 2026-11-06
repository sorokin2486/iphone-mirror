# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Тест защиты от повторного запуска."""
from __future__ import annotations

import time
import uuid

from PySide6.QtCore import QCoreApplication

from app.single_instance import InstanceServer, notify_running_instance


def test_second_instance_activates_first():
    app = QCoreApplication.instance() or QCoreApplication([])
    name = f"iPhoneMirror-test-{uuid.uuid4().hex}"
    assert notify_running_instance(name) is False      # никого нет

    server = InstanceServer(name)
    assert server.listen()
    events = []
    server.activate_requested.connect(lambda: events.append("activate"))

    assert notify_running_instance(name) is True
    deadline = time.time() + 3
    while not events and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert events == ["activate"]
