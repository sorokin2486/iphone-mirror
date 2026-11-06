# Сторонние компоненты / Third-party components

iPhone Mirror распространяется под лицензией GPL-3.0 (см. `LICENSE`).
Сборка (.exe и установщик) включает следующие компоненты:

| Компонент | Лицензия | Исходный код |
|---|---|---|
| UxPlay (AirPlay-приёмник) | GPL-3.0 | https://github.com/FDH2/UxPlay |
| GStreamer и плагины (base/good/bad/libav) | LGPL-2.1+ | https://gstreamer.freedesktop.org/src/ |
| FFmpeg (в составе gst-libav и PyAV) | LGPL-2.1+ / GPL-2.0+ (в зависимости от сборки) | https://ffmpeg.org/download.html |
| libplist | LGPL-2.1+ | https://github.com/libimobiledevice/libplist |
| OpenSSL | Apache-2.0 | https://www.openssl.org/source/ |
| Прочие DLL из MSYS2 (glib, pango, cairo и др.) | разные свободные лицензии | https://packages.msys2.org/ |
| Qt 6 / PySide6 | LGPL-3.0 | https://code.qt.io/ |
| PyAV | BSD-3-Clause | https://github.com/PyAV-Org/PyAV |
| NumPy | BSD-3-Clause | https://github.com/numpy/numpy |
| Python | PSF License | https://www.python.org/ |

Двоичные файлы UxPlay и GStreamer собираются из исходников скриптами
`setup/install.ps1`, `setup/build_uxplay.sh` и `setup/bundle_uxplay.sh`.

AirPlay — торговая марка Apple Inc. Проект не связан с Apple и не одобрен ею.
