# Установка зависимостей iPhone Mirror:
#   1) Python-пакеты (PySide6, PyAV, numpy)
#   2) MSYS2 (через winget), если его нет
#   3) Сборка AirPlay-приёмника UxPlay с GStreamer
# Запуск:  powershell -ExecutionPolicy Bypass -File setup\install.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$msys = "C:\msys64"
$bash = Join-Path $msys "usr\bin\bash.exe"

Write-Host "==> [1/3] Python-зависимости" -ForegroundColor Cyan
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    python -m venv (Join-Path $root ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Не удалось создать .venv (нужен Python 3.10+)" }
}
& $venvPy -m pip install --upgrade -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install завершился с ошибкой" }

Write-Host "==> [2/3] MSYS2" -ForegroundColor Cyan
if (-not (Test-Path $bash)) {
    winget install -e --id MSYS2.MSYS2 --accept-source-agreements --accept-package-agreements
    if (-not (Test-Path $bash)) { throw "MSYS2 не установился. Поставьте вручную с https://www.msys2.org и запустите скрипт снова." }
}

function Invoke-Msys([string]$cmd, [int]$attempts = 3) {
    $env:MSYSTEM = "UCRT64"
    $env:CHERE_INVOKING = "1"
    for ($i = 1; $i -le $attempts; $i++) {
        & $bash -lc $cmd
        if ($LASTEXITCODE -eq 0) { return }
        Write-Host "    Попытка $i из $attempts не удалась (часто это медленное зеркало), повторяю..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
    throw "Команда MSYS2 завершилась с ошибкой: $cmd"
}

# mirror.msys2.org бывает недоступен (обрывы SSL) — ставим зеркало Яндекса первым.
function Set-PreferredMirror([string]$file, [string]$server) {
    $path = Join-Path $msys "etc\pacman.d\$file"
    if (-not (Test-Path $path)) { return }
    $lines = Get-Content $path
    if ($lines -contains $server) { $lines = $lines | Where-Object { $_ -ne $server } }
    $result = @("# preferred by iPhone Mirror installer", $server) + ($lines | Where-Object { $_ -ne "# preferred by iPhone Mirror installer" })
    [IO.File]::WriteAllLines($path, $result)
}
Set-PreferredMirror "mirrorlist.mingw" 'Server = https://mirror.yandex.ru/mirrors/msys2/mingw/$repo/'
Set-PreferredMirror "mirrorlist.msys"  'Server = https://mirror.yandex.ru/mirrors/msys2/msys/$arch/'

Write-Host "    Обновление MSYS2 (два прохода, это нормально)..."
Invoke-Msys "pacman -Syu --noconfirm --disable-download-timeout"
Invoke-Msys "pacman -Syu --noconfirm --disable-download-timeout"

Write-Host "==> [3/3] Сборка UxPlay" -ForegroundColor Cyan
# Запускаем из папки setup (CHERE_INVOKING=1 сохраняет текущий каталог),
# чтобы не передавать путь с пробелами через кавычки PowerShell 5.1.
Push-Location $PSScriptRoot
[Environment]::CurrentDirectory = $PSScriptRoot
try { Invoke-Msys "bash ./build_uxplay.sh" } finally { Pop-Location }

Write-Host ""
Write-Host "Готово! Запускайте run.bat" -ForegroundColor Green
Write-Host "При первом запуске Windows спросит разрешение для uxplay.exe в брандмауэре - разрешите для частных сетей."
