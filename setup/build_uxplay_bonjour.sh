#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
# Сборка варианта UxPlay, который объявляет себя через системную службу Bonjour
# (cmake -DUSE_DNS_SD=1) -> /ucrt64/bin/uxplay-bonjour.exe.
#
# Зачем: встроенный mDNS UxPlay шлёт объявления по маршруту multicast по умолчанию —
# при VPN в режиме TUN они уходят в туннель, а не в домашнюю сеть / USB, и iPhone
# не видит ПК. Кроме того, запущенный Bonjour (mDNSResponder) забирает себе
# входящие mDNS-запросы на порт 5353. Bonjour же объявляет службу на всех интерфейсах.
#
# Официальный Bonjour SDK требует Apple ID, поэтому собираем минимальный «SDK»:
#   Include/dns_sd.h — из открытого исходника Apple mDNSResponder (BSD-3-Clause),
#   Lib/x64/dnssd.lib — импорт-библиотека, сгенерированная из системной dnssd.dll.
set -euo pipefail

SRC="$HOME/UxPlay"
SDK="$HOME/bonjour-sdk"
DLL="$(cygpath -u "${SYSTEMROOT:-C:/Windows}")/System32/dnssd.dll"
HEADER_URL="https://raw.githubusercontent.com/apple-oss-distributions/mDNSResponder/main/mDNSShared/dns_sd.h"

[ -d "$SRC/.git" ] || { echo "Сначала соберите обычный UxPlay (build_uxplay.sh)"; exit 1; }
[ -f "$DLL" ] || { echo "Нет $DLL — установите Bonjour (iTunes / «Устройства Apple»)"; exit 1; }

pacman -S --needed --noconfirm --disable-download-timeout mingw-w64-ucrt-x86_64-tools-git

echo "==> Мини-SDK Bonjour"
mkdir -p "$SDK/Include" "$SDK/Lib/x64"
curl -fsSL --retry 3 -o "$SDK/Include/dns_sd.h" "$HEADER_URL"
( cd "$SDK/Lib/x64" && gendef - "$DLL" > dnssd.def && dlltool -d dnssd.def -D dnssd.dll -l dnssd.lib )

echo "==> Сборка UxPlay с Bonjour"
export BONJOUR_SDK_HOME="$(cygpath -m "$SDK")"
cmake -S "$SRC" -B "$SRC/build-dnssd" -G Ninja -DCMAKE_BUILD_TYPE=Release -DUSE_DNS_SD=1
cmake --build "$SRC/build-dnssd"
cp -f "$SRC/build-dnssd/uxplay.exe" /ucrt64/bin/uxplay-bonjour.exe
echo "==> Готово: $(cygpath -w /ucrt64/bin/uxplay-bonjour.exe)"
