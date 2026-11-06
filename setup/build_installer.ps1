# Сборка установщика dist\iPhoneMirror-Setup-<версия>.exe (Inno Setup 6).
# Сначала нужно собрать приложение: setup\build_exe.ps1  (или передайте -BuildExe).
# Запуск:  powershell -ExecutionPolicy Bypass -File setup\build_installer.ps1 [-BuildExe]
param([switch]$BuildExe)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if ($BuildExe) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build_exe.ps1")
    if ($LASTEXITCODE -ne 0) { throw "build_exe.ps1 завершился с ошибкой" }
}
if (-not (Test-Path (Join-Path $root "dist\iPhone Mirror\iPhone Mirror.exe"))) {
    throw "Нет dist\iPhone Mirror — сначала запустите setup\build_exe.ps1 (или добавьте -BuildExe)"
}

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Host "Inno Setup не найден, устанавливаю через winget..."
    winget install -e --id JRSoftware.InnoSetup --accept-source-agreements --accept-package-agreements --silent
    $iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $iscc)) { throw "Не удалось установить Inno Setup" }
}

$version = (& (Join-Path $root ".venv\Scripts\python.exe") -c "import sys; sys.path.insert(0, r'$root'); import app; print(app.__version__)").Trim()
Write-Host "==> Сборка установщика v$version" -ForegroundColor Cyan
& $iscc "/DAppVersion=$version" (Join-Path $root "installer\iPhoneMirror.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC завершился с ошибкой" }

$setup = Join-Path $root "dist\iPhoneMirror-Setup-$version.exe"
Write-Host ""
Write-Host ("Готово: {0}  ({1:N1} МБ)" -f $setup, ((Get-Item $setup).Length / 1MB)) -ForegroundColor Green
