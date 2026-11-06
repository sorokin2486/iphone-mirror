#!/usr/bin/env bash
# Собирает переносимый комплект UxPlay + GStreamer (только нужные плагины и их DLL)
# в каталог $1. Запускается в MSYS2 UCRT64 из build_exe.ps1.
set -euo pipefail

OUT="${1:?usage: bundle_uxplay.sh <out-dir>}"
PREFIX=/ucrt64
PLUGINS=(
  app audioconvert audioparsers audioresample autodetect coreelements
  d3d11 d3d12 directsound imagefreeze jpeg level libav pango playback rtp tcp
  typefindfunctions videoconvertscale videofilter videoparsersbad volume
  wasapi wasapi2
)

rm -rf "$OUT"
mkdir -p "$OUT/bin" "$OUT/lib/gstreamer-1.0" "$OUT/libexec/gstreamer-1.0" "$OUT/etc"

cp "$PREFIX/bin/uxplay.exe" "$OUT/bin/"
# Вариант с Bonjour (если собран): зависит от системной dnssd.dll, её не копируем.
if [ -f "$PREFIX/bin/uxplay-bonjour.exe" ]; then
  cp "$PREFIX/bin/uxplay-bonjour.exe" "$OUT/bin/"
else
  echo "WARN: нет uxplay-bonjour.exe (setup/build_uxplay_bonjour.sh) — будет только встроенный mDNS"
fi
cp "$PREFIX/libexec/gstreamer-1.0/gst-plugin-scanner.exe" "$OUT/libexec/gstreamer-1.0/"
for p in "${PLUGINS[@]}"; do
  f="$PREFIX/lib/gstreamer-1.0/libgst$p.dll"
  if [ -f "$f" ]; then cp "$f" "$OUT/lib/gstreamer-1.0/"; else echo "WARN: нет плагина $p"; fi
done
cp -r "$PREFIX/etc/fonts" "$OUT/etc/" 2>/dev/null || true

# Все DLL из /ucrt64/bin, от которых (транзитивно) зависят exe и плагины.
deps=$(for f in "$OUT"/bin/*.exe "$OUT"/libexec/gstreamer-1.0/*.exe "$OUT"/lib/gstreamer-1.0/*.dll; do
  ldd "$f" | awk '$3 ~ /^\/ucrt64\/bin\// {print $3}'
done | sort -u)
for d in $deps; do cp -n "$d" "$OUT/bin/"; done

echo "==> Комплект UxPlay: $(du -sh "$OUT" | cut -f1), DLL: $(ls "$OUT/bin" | wc -l)"
