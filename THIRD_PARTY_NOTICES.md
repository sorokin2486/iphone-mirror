# Third-party components / Сторонние компоненты

**iPhone Mirror** — © 2026 Сорокин Иван / Ivan Sorokin (**sorokin dev**).
Licensed under GPL-3.0-or-later (see `LICENSE`) / распространяется под GPL-3.0-or-later.

The app build (.exe and installer) bundles the following components /
сборка (.exe и установщик) включает следующие компоненты:

| Component / Компонент | License / Лицензия | Source / Исходный код |
|---|---|---|
| UxPlay (AirPlay receiver) | GPL-3.0 | https://github.com/FDH2/UxPlay |
| GStreamer + plugins (base/good/bad/libav) | LGPL-2.1+ | https://gstreamer.freedesktop.org/src/ |
| FFmpeg (in gst-libav and PyAV) | LGPL-2.1+ / GPL-2.0+ (build-dependent) | https://ffmpeg.org/download.html |
| libplist | LGPL-2.1+ | https://github.com/libimobiledevice/libplist |
| OpenSSL | Apache-2.0 | https://www.openssl.org/source/ |
| Other MSYS2 DLLs (glib, pango, cairo, …) | various free licenses | https://packages.msys2.org/ |
| `dns_sd.h` (Apple mDNSResponder, build-time only) | BSD-3-Clause | https://github.com/apple-oss-distributions/mDNSResponder |
| Qt 6 / PySide6 | LGPL-3.0 | https://code.qt.io/ |
| PyAV | BSD-3-Clause | https://github.com/PyAV-Org/PyAV |
| NumPy | BSD-3-Clause | https://github.com/numpy/numpy |
| Python | PSF License | https://www.python.org/ |

UxPlay and GStreamer binaries are built from source by `setup/install.ps1`,
`setup/build_uxplay.sh`, `setup/build_uxplay_bonjour.sh` and `setup/bundle_uxplay.sh`.
The Bonjour runtime (`dnssd.dll`) is **not** redistributed — it is used only if already installed.

The "sorokin dev" logo is © Сорокин Иван and is not covered by the GPL.
Логотип «sorokin dev» принадлежит Сорокину Ивану и не распространяется под GPL.

AirPlay and iPhone are trademarks of Apple Inc. This project is not affiliated with or endorsed by Apple.
AirPlay и iPhone — торговые марки Apple Inc. Проект не связан с Apple и не одобрен ею.
