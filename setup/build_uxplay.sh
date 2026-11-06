#!/usr/bin/env bash
# Сборка UxPlay в MSYS2 (окружение UCRT64). Запускается из setup/install.ps1.
set -euo pipefail

PKGS=(
  git
  mingw-w64-ucrt-x86_64-cmake
  mingw-w64-ucrt-x86_64-gcc
  mingw-w64-ucrt-x86_64-ninja
  mingw-w64-ucrt-x86_64-pkgconf
  mingw-w64-ucrt-x86_64-libplist
  mingw-w64-ucrt-x86_64-openssl
  mingw-w64-ucrt-x86_64-gstreamer
  mingw-w64-ucrt-x86_64-gst-plugins-base
  mingw-w64-ucrt-x86_64-gst-plugins-good
  mingw-w64-ucrt-x86_64-gst-plugins-bad
  mingw-w64-ucrt-x86_64-gst-libav
)

echo "==> Установка пакетов MSYS2"
pacman -S --needed --noconfirm --disable-download-timeout "${PKGS[@]}"

SRC="$HOME/UxPlay"
if [ -d "$SRC/.git" ]; then
  echo "==> Обновление исходников UxPlay"
  git -C "$SRC" pull --ff-only
else
  echo "==> Загрузка исходников UxPlay"
  git clone --depth 1 https://github.com/FDH2/UxPlay.git "$SRC"
fi

echo "==> Сборка UxPlay"
cmake -S "$SRC" -B "$SRC/build" -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build "$SRC/build"
cp -f "$SRC/build/uxplay.exe" /ucrt64/bin/uxplay.exe

echo "==> Готово: $(cygpath -w /ucrt64/bin/uxplay.exe)"
/ucrt64/bin/uxplay.exe -v || true
