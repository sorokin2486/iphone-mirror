# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Точка входа для PyInstaller (и просто `python iphone_mirror.py`)."""
import sys

from app.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
