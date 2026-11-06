# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
"""Генерирует файл версии Windows для PyInstaller (--version-file):
автор, копирайт и версия видны в «Свойства файла → Подробно»."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041904B0', [
      StringStruct('CompanyName', {company!r}),
      StringStruct('FileDescription', 'iPhone Mirror — экран и звук iPhone на Windows'),
      StringStruct('FileVersion', {ver!r}),
      StringStruct('InternalName', 'iPhone Mirror'),
      StringStruct('LegalCopyright', {copyright!r}),
      StringStruct('OriginalFilename', 'iPhone Mirror.exe'),
      StringStruct('ProductName', 'iPhone Mirror'),
      StringStruct('ProductVersion', {ver!r}),
      StringStruct('Comments', {url!r})])]),
    VarFileInfo([VarStruct('Translation', [0x0419, 1200])])
  ]
)
"""


def main(out: str) -> None:
    parts = [int(x) for x in app.__version__.split(".")][:4]
    tup = tuple(parts + [0] * (4 - len(parts)))
    text = TEMPLATE.format(tup=tup, ver=app.__version__, url=app.__url__,
                           company=f"{app.__author__} ({app.__brand__})",
                           copyright=f"{app.__copyright__}. GPL-3.0")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(text, encoding="utf-8")
    print("version file ->", out)


if __name__ == "__main__":
    main(sys.argv[1])
