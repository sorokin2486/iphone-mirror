"""Управление процессом UxPlay (AirPlay-приёмник).

UxPlay сам принимает AirPlay-поток от iPhone, расшифровывает его и играет звук.
Видео (H.264) через опцию -vrtp пересылается нам по локальному TCP в виде
Annex-B потока, который декодирует app/video_stream.py.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from .config import AppConfig
from .paths import BUNDLED_UXPLAY, BUNDLED_UXPLAY_DIR, gstreamer_env
from .win_job import KillOnCloseJob

log = logging.getLogger(__name__)

MSYS_CANDIDATES = (
    Path(r"C:\msys64\ucrt64\bin\uxplay.exe"),
    Path(r"C:\msys64\mingw64\bin\uxplay.exe"),
    Path(r"C:\msys64\clang64\bin\uxplay.exe"),
)
LOG_LIMIT = 2000
STOP_TIMEOUT_MS = 3000


def find_uxplay(cfg: AppConfig) -> Path | None:
    if cfg.uxplay_path:
        p = Path(cfg.uxplay_path)
        return p if p.is_file() else None
    if BUNDLED_UXPLAY.is_file():          # комплект внутри .exe
        return BUNDLED_UXPLAY
    found = shutil.which("uxplay")
    if found:
        return Path(found)
    return next((p for p in MSYS_CANDIDATES if p.is_file()), None)


def video_forward_pipeline(port: int) -> str:
    """Хвост GStreamer-пайплайна после `rtph264pay` (см. -vrtp в UxPlay).

    rtp-упаковку сразу распаковываем обратно и отдаём сырой H.264 (byte-stream)
    в наш TCP-сервер. SPS/PPS повторяются перед каждым ключевым кадром,
    чтобы декодер мог подхватить поток в любой момент.
    """
    return (
        "config-interval=-1 ! rtph264depay ! h264parse config-interval=-1 ! "
        "video/x-h264,stream-format=byte-stream,alignment=au ! "
        f"tcpclientsink host=127.0.0.1 port={int(port)} sync=false"
    )


def build_uxplay_args(cfg: AppConfig) -> list[str]:
    args = [
        "-n", cfg.device_name,
        "-nh",                       # не дописывать @hostname к имени
        "-nohold",                   # новое подключение вытесняет старое
        "-p",                        # фиксированные порты (7000/7001/7100, 6000/6001/7011)
        "-s", cfg.max_resolution,
        "-fps", str(cfg.fps),
        "-vrtp", video_forward_pipeline(cfg.video_port),
    ]
    if not cfg.audio_enabled:
        args += ["-as", "0"]
    return args


class UxPlayReceiver(QObject):
    log_line = Signal(str)
    status_changed = Signal(str)      # "running" | "stopped" | "missing" | "error"
    client_event = Signal(str)        # текстовые события о подключении клиента

    def __init__(self, cfg: AppConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._proc: QProcess | None = None
        self._lines: list[str] = []
        self._stopping = False
        self._job = KillOnCloseJob()

    @property
    def lines(self) -> list[str]:
        return list(self._lines)

    def update_config(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.state() != QProcess.NotRunning

    def start(self) -> None:
        if self.is_running():
            return
        exe = find_uxplay(self._cfg)
        if exe is None:
            self._emit_log("UxPlay не найден. Запустите setup\\install.ps1 (см. README).")
            self.status_changed.emit("missing")
            return
        proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PATH", str(exe.parent) + os.pathsep + env.value("PATH"))
        if exe == BUNDLED_UXPLAY:
            for key, value in gstreamer_env(BUNDLED_UXPLAY_DIR).items():
                env.insert(key, value)
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read_output)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)
        args = build_uxplay_args(self._cfg)
        self._emit_log(f"> {exe} {' '.join(args)}")
        self._stopping = False
        self._proc = proc
        proc.start(str(exe), args)
        if proc.waitForStarted(5000):
            self._job.assign(int(proc.processId()))
            self.status_changed.emit("running")

    def stop(self) -> None:
        proc = self._proc
        if proc is None:
            return
        self._stopping = True
        if proc.state() != QProcess.NotRunning:
            # Консольный uxplay.exe на Windows игнорирует WM_CLOSE (terminate),
            # поэтому завершаем принудительно.
            proc.kill()
            proc.waitForFinished(STOP_TIMEOUT_MS)
        self._proc = None
        self.status_changed.emit("stopped")

    def restart(self) -> None:
        self.stop()
        self.start()

    # --- внутреннее -------------------------------------------------------
    def _read_output(self) -> None:
        if self._proc is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self._emit_log(line)
                self._detect_client_event(line)

    def _detect_client_event(self, line: str) -> None:
        low = line.lower()
        if "connection request" in low or "accepted ipv" in low:
            self.client_event.emit("connecting")
        elif "connection closed" in low or "client disconnected" in low or "teardown" in low:
            self.client_event.emit("closed")

    def _emit_log(self, line: str) -> None:
        self._lines = (self._lines + [line])[-LOG_LIMIT:]
        self.log_line.emit(line)

    def _on_finished(self, code: int, _status) -> None:
        if self._stopping:
            return
        self._emit_log(f"UxPlay завершился (код {code}).")
        self._proc = None
        self.status_changed.emit("error")

    def _on_error(self, error) -> None:
        if self._stopping:
            return
        self._emit_log(f"Ошибка процесса UxPlay: {error}")
        self.status_changed.emit("error")
