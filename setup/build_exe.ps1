# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Сорокин Иван (sorokin dev)
# Сборка переносимого приложения: dist\iPhone Mirror\iPhone Mirror.exe
# Требует: выполненный setup\install.ps1 (MSYS2 + собранный UxPlay, .venv).
# Запуск:  powershell -ExecutionPolicy Bypass -File setup\build_exe.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$bash = "C:\msys64\usr\bin\bash.exe"
$bundle = Join-Path $root "build\uxplay_bundle"

if (-not (Test-Path $py)) { throw "Нет .venv — сначала запустите setup\install.ps1" }
if (-not (Test-Path "C:\msys64\ucrt64\bin\uxplay.exe")) { throw "UxPlay не собран — сначала запустите setup\install.ps1" }

Write-Host "==> [1/4] PyInstaller" -ForegroundColor Cyan
& $py -m pip install --upgrade "pyinstaller>=6.10"
if ($LASTEXITCODE -ne 0) { throw "Не удалось установить PyInstaller" }

Write-Host "==> [2/4] Комплект UxPlay + GStreamer" -ForegroundColor Cyan
$env:MSYSTEM = "UCRT64"
$env:CHERE_INVOKING = "1"
Push-Location $PSScriptRoot
[Environment]::CurrentDirectory = $PSScriptRoot
try {
    & $bash -lc "bash ./bundle_uxplay.sh ../build/uxplay_bundle"
    if ($LASTEXITCODE -ne 0) { throw "Сборка комплекта UxPlay не удалась" }
} finally { Pop-Location }

Write-Host "==> [3/4] Логотип, иконка, сведения о версии" -ForegroundColor Cyan
& $py (Join-Path $PSScriptRoot "make_brand_assets.py")
if ($LASTEXITCODE -ne 0) { throw "Не удалось подготовить логотип" }
& $py (Join-Path $PSScriptRoot "make_icon.py")
if ($LASTEXITCODE -ne 0) { throw "Не удалось создать иконку" }
$versionFile = Join-Path $root "build\version_info.txt"
& $py (Join-Path $PSScriptRoot "version_info.py") $versionFile
if ($LASTEXITCODE -ne 0) { throw "Не удалось создать файл версии" }

Write-Host "==> [4/4] Сборка .exe" -ForegroundColor Cyan
Push-Location $root
[Environment]::CurrentDirectory = $root
try {
    & $py -m PyInstaller --noconfirm --clean --windowed `
        --name "iPhone Mirror" `
        --icon (Join-Path $root "assets\icon.ico") `
        --version-file $versionFile `
        --add-data ((Join-Path $root "assets") + ";assets") `
        --exclude-module tkinter `
        --distpath dist --workpath "build\pyinstaller" --specpath build `
        iphone_mirror.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller завершился с ошибкой" }
} finally { Pop-Location }

$internal = Join-Path $root "dist\iPhone Mirror\_internal"

# Комплект UxPlay копируем после PyInstaller: иначе он «анализирует» эти DLL
# и дублирует их в корень _internal (+~180 МБ).
Write-Host "    Копирование UxPlay в сборку..."
Copy-Item $bundle (Join-Path $internal "uxplay") -Recurse -Force

# Части Qt, которые приложению не нужны (QML/Quick, PDF, сеть/TLS,
# программный OpenGL, мультимедийный ffmpeg Qt, лишние платформы).
$qt = Join-Path $internal "PySide6"
$unused = @(
    "opengl32sw.dll", "Qt6Pdf.dll", "Qt6Qml.dll", "Qt6QmlMeta.dll", "Qt6QmlModels.dll",
    "Qt6QmlWorkerScript.dll", "Qt6Quick.dll", "Qt6VirtualKeyboard.dll",
    "avcodec-*.dll", "avformat-*.dll", "avutil-*.dll", "swresample-*.dll", "swscale-*.dll",
    "plugins\imageformats\qpdf.dll", "plugins\platforminputcontexts", "plugins\tls",
    "plugins\networkinformation", "plugins\generic", "plugins\platforms\qdirect2d.dll",
    "plugins\platforms\qminimal.dll", "plugins\platforms\qoffscreen.dll"
)
foreach ($item in $unused) {
    Get-ChildItem (Join-Path $qt $item) -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
}

$exe = Join-Path $root "dist\iPhone Mirror\iPhone Mirror.exe"
$size = [math]::Round(((Get-ChildItem (Split-Path $exe) -Recurse | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host ""
Write-Host "Готово: $exe  ($size МБ)" -ForegroundColor Green
Write-Host "Всю папка 'dist\iPhone Mirror' можно копировать на другой ПК — Python и MSYS2 не нужны."
