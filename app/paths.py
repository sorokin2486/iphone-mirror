# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Пути приложения: работа из исходников и из собранного .exe (PyInstaller)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "iPhone Mirror"
IS_FROZEN = getattr(sys, "frozen", False)

# Ресурсы: внутри .exe — каталог _internal (sys._MEIPASS), иначе корень проекта.
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ICON_PATH = RESOURCE_DIR / "assets" / "icon.png"
LOGO_PATH = RESOURCE_DIR / "assets" / "logo-dark.png"
BUNDLED_UXPLAY_DIR = RESOURCE_DIR / "uxplay"
BUNDLED_UXPLAY = BUNDLED_UXPLAY_DIR / "bin" / "uxplay.exe"


def user_data_dir() -> Path:
    """Куда писать config.json: рядом с проектом в dev-режиме, в %APPDATA% в .exe."""
    if not IS_FROZEN:
        return RESOURCE_DIR
    base = Path(os.environ.get("APPDATA") or Path.home())
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def gstreamer_env(bundle_dir: Path) -> dict[str, str]:
    """Переменные окружения для переносимого GStreamer из комплекта."""
    cache = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / APP_NAME
    cache.mkdir(parents=True, exist_ok=True)
    return {
        "GST_PLUGIN_SYSTEM_PATH_1_0": str(bundle_dir / "lib" / "gstreamer-1.0"),
        "GST_PLUGIN_PATH_1_0": "",
        "GST_PLUGIN_SCANNER_1_0": str(bundle_dir / "libexec" / "gstreamer-1.0" / "gst-plugin-scanner.exe"),
        "GST_REGISTRY_1_0": str(cache / "gst-registry.bin"),
        "FONTCONFIG_PATH": str(bundle_dir / "etc" / "fonts"),
    }
