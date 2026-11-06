"""Точка входа для PyInstaller (и просто `python iphone_mirror.py`)."""
import sys

from app.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
