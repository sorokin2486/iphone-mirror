# iPhone Mirror

Вывод экрана и звука iPhone на Windows-ПК — по Wi‑Fi, через стандартный «Повтор экрана» (AirPlay),
как ApowerMirror. Картинка показывается в окне, нарисованном в виде iPhone (титановая рамка,
Dynamic Island, кнопки), окно само поворачивается в ландшафт, когда поворачиваете телефон.

## Скачать

Готовый установщик — на странице **Releases** (`iPhoneMirror-Setup-<версия>.exe`).
Python, MSYS2 и GStreamer ставить не нужно: всё уже внутри. При установке можно
отметить «Разрешить в брандмауэре», чтобы iPhone сразу увидел ПК.

Требования: Windows 10/11 x64, iPhone/iPad с iOS 12+ в той же Wi‑Fi‑сети.

## Подключение по кабелю (USB)

Можно обойтись без Wi‑Fi и роутера — трансляция идёт прямо по кабелю:

1. На iPhone: **Настройки → Режим модема → «Разрешать другим»** — включить.
2. Подключите iPhone к ПК кабелем и нажмите на iPhone «Доверять».
3. В окне появится зелёная плашка **USB** (приложение само находит сеть iPhone
   `172.20.10.0/28` и перезапускает приёмник, чтобы iPhone его увидел).
4. **Пункт управления → Повтор экрана → «iPhone Mirror PC»**.

Нужно:
* драйвер Apple — приложение «Устройства Apple» (Microsoft Store) или iTunes;
* на iPhone должен быть доступен «Режим модема» (зависит от оператора/SIM).

Видео идёт по кабелю и мобильный трафик не тратит. Если Windows начнёт ходить в интернет
через iPhone, выключите на iPhone «Сотовые данные» — трансляции это не мешает.
Установщик добавляет для этого правило брандмауэра, разрешающее UxPlay только
подсеть iPhone (`172.20.10.0/28`), т.к. Windows обычно считает эту сеть «общедоступной».

Почему не «чистый» USB, как у QuickTime на Mac: на Windows для этого пришлось бы заменить
драйвер Apple на WinUSB, после чего перестанут работать iTunes/«Устройства Apple».

## VPN

Сам поток идёт по локальной сети, VPN его обычно не трогает. Проблема бывает с **поиском**:
iPhone находит ПК по mDNS (multicast), а VPN в режиме TUN (sing-box, MantaRay, Hiddify…)
забирает себе маршрут multicast — объявления уходят в туннель, и iPhone ПК не видит.

Поэтому, если на ПК есть служба **Bonjour** (ставится с iTunes / «Устройствами Apple»),
приложение использует вариант UxPlay, который объявляет себя через Bonjour — он рассылает
объявления во все сети (Ethernet, Wi‑Fi, USB) независимо от VPN. Без Bonjour используется
встроенный mDNS. Режим можно задать в `config.json`: `"mdns_mode": "auto" | "bonjour" | "internal"`.

На iPhone VPN мешает, только если в нём включено «блокировать локальную сеть» / kill switch.

## Как это устроено

```
iPhone ──AirPlay (Wi‑Fi)──► uxplay.exe ──► звук: сразу в колонки ПК
                               │
                               └─ видео H.264 (-vrtp → TCP 127.0.0.1:47011)
                                          │
                                          ▼
                     app (Python/PySide6): PyAV декодирует → окно‑iPhone
```

* **UxPlay** — открытый AirPlay‑приёмник (GPL‑3, https://github.com/FDH2/UxPlay). Он делает
  самое сложное: рукопожатие AirPlay, расшифровку потока и воспроизведение звука.
* **Приложение** запускает UxPlay, забирает у него видеопоток и рисует его внутри «айфона».

## Установка (один раз)

Нужен Python 3.10+ (у вас 3.12 — подходит) и интернет.

```powershell
powershell -ExecutionPolicy Bypass -File setup\install.ps1
```

Скрипт:
1. создаёт `.venv` и ставит PySide6, PyAV, numpy;
2. ставит MSYS2 через `winget` (если его нет);
3. ставит GStreamer и собирает `uxplay.exe` → `C:\msys64\ucrt64\bin\uxplay.exe`.

Сборка занимает ~5–15 минут.

## Готовое приложение (.exe)

```powershell
powershell -ExecutionPolicy Bypass -File setup\build_exe.ps1
```

Результат — папка `dist\iPhone Mirror\` (~350 МБ) с `iPhone Mirror.exe`.
Внутри уже есть UxPlay и нужная часть GStreamer, поэтому на другом ПК **не нужны**
ни Python, ни MSYS2 — достаточно скопировать всю папку. Настройки .exe хранит в
`%APPDATA%\iPhone Mirror\config.json`.

Скрипт: ставит PyInstaller в `.venv`, собирает переносимый комплект UxPlay
(`setup\bundle_uxplay.sh` — только нужные плагины и их DLL), рисует иконку
(`setup\make_icon.py`) и упаковывает приложение.

## Установщик

```powershell
powershell -ExecutionPolicy Bypass -File setup\build_installer.ps1 -BuildExe
```

Собирает `.exe` и упаковывает его в `dist\iPhoneMirror-Setup-<версия>.exe` (Inno Setup 6,
ставится автоматически через winget). Версия берётся из `app/__init__.py`.

## Запуск из исходников

* `run.bat` — обычный запуск (без консоли);
* `run_debug.bat` — с консолью, если что-то не работает.

При первом запуске Windows спросит доступ в сеть для `uxplay.exe` — **разрешите для частных сетей**,
иначе iPhone не увидит ПК.

На iPhone: **Пункт управления → Повтор экрана → «iPhone Mirror PC»**.
iPhone и ПК должны быть в одной Wi‑Fi‑сети.

## Управление

| Действие | Как |
|---|---|
| Двигать окно | зажать ЛКМ на телефоне |
| Масштаб | Ctrl + колесо мыши, или ПКМ → Размер |
| Меню | ПКМ: поверх всех окон, цвет корпуса, звук вкл/выкл, имя приёмника, журнал, перезапуск |
| Скриншот экрана iPhone | Ctrl+S (сохраняется в `Изображения\iPhone Mirror`) |
| Свернуть | двойной клик |
| Выход | Ctrl+Q |

Настройки сохраняются в `config.json` (создаётся автоматически):
`device_name`, `video_port`, `max_resolution` (по умолчанию `1920x1920`, чтобы и портрет,
и ландшафт были чёткими), `fps`, `audio_enabled`, `uxplay_path` (если uxplay лежит в другом месте).

## Если не работает

* **iPhone не видит ПК** — проверьте брандмауэр (порты UxPlay: TCP 7000, 7001, 7100; UDP 6000, 6001, 7011),
  одну сеть, и что роутер не изолирует клиентов Wi‑Fi.
* **Подключается, но чёрный экран** — откройте ПКМ → «Журнал UxPlay». Чаще всего не хватает
  плагина GStreamer: перезапустите `setup\install.ps1`.
* **Звук есть, видео нет** — порт 47011 занят: поменяйте `video_port` в `config.json`.

## Разработка

```powershell
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest -q
```

Структура:

```
app/
  __main__.py      точка входа, связывает всё вместе
  config.py        настройки (immutable dataclass + config.json)
  receiver.py      запуск/остановка UxPlay, аргументы командной строки, журнал
  video_stream.py  TCP‑сервер + H.264‑декодер (PyAV), только последний кадр
  phone_skin.py    геометрия и отрисовка корпуса iPhone
  lock_screen.py   заглушка «экран блокировки», пока нет трансляции
  phone_view.py    виджет: корпус + видео, поворот в ландшафт
  main_window.py   безрамочное окно, меню, масштаб, скриншоты
  paths.py         пути для режима исходников и .exe
  win_job.py       Job Object: uxplay.exe завершается вместе с приложением
  usb_link.py      определение iPhone по кабелю / через точку доступа
  bonjour.py       выбор объявления в сети: Bonjour или встроенный mDNS
assets/            иконка
iphone_mirror.py   точка входа для PyInstaller
setup/
  install.ps1      установка всего
  build_uxplay.sh  сборка UxPlay в MSYS2
  build_uxplay_bonjour.sh  вариант UxPlay с Bonjour (uxplay-bonjour.exe)
  build_exe.ps1    сборка .exe
  bundle_uxplay.sh переносимый комплект UxPlay + GStreamer
  make_icon.py     генерация иконки
  build_installer.ps1  сборка установщика
installer/
  iPhoneMirror.iss скрипт Inno Setup
tests/test_core.py
```

## Лицензия

GPL-3.0 (см. `LICENSE`) — проект встраивает UxPlay, распространяемый под GPL-3.0.
Список сторонних компонентов и их лицензий — в `THIRD_PARTY_NOTICES.md`.
AirPlay — торговая марка Apple Inc.; проект не связан с Apple.
