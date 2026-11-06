"""Настройки приложения: неизменяемый dataclass + загрузка/сохранение в config.json."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

from .paths import user_data_dir

log = logging.getLogger(__name__)

CONFIG_PATH = user_data_dir() / "config.json"

SCALE_MIN = 0.3
SCALE_MAX = 1.6
PORT_MIN = 1024
PORT_MAX = 65535


@dataclass(frozen=True)
class AppConfig:
    device_name: str = "iPhone Mirror PC"   # имя приёмника в «Повторе экрана»
    uxplay_path: str = ""                   # пусто = автопоиск
    video_port: int = 47011                 # локальный TCP-порт для видео UxPlay -> приложение
    max_resolution: str = "1920x1920"       # -s: квадрат, чтобы и портрет, и ландшафт были чёткими
    fps: int = 60
    audio_enabled: bool = True
    always_on_top: bool = False
    scale: float = 0.8                      # масштаб «корпуса» телефона
    model_color: str = "natural"            # natural | black | white | blue
    window_x: int = -1
    window_y: int = -1

    def with_changes(self, **changes) -> "AppConfig":
        return validate(replace(self, **changes))


COLORS = ("natural", "black", "white", "blue")


def validate(cfg: AppConfig) -> AppConfig:
    """Возвращает копию с безопасными значениями (ничего не мутирует)."""
    name = cfg.device_name.strip()[:40] or AppConfig.device_name
    port = cfg.video_port if PORT_MIN <= cfg.video_port <= PORT_MAX else AppConfig.video_port
    scale = min(max(float(cfg.scale), SCALE_MIN), SCALE_MAX)
    fps = min(max(int(cfg.fps), 15), 120)
    res = cfg.max_resolution if _valid_resolution(cfg.max_resolution) else AppConfig.max_resolution
    color = cfg.model_color if cfg.model_color in COLORS else AppConfig.model_color
    return replace(cfg, device_name=name, video_port=port, scale=scale, fps=fps,
                   max_resolution=res, model_color=color)


def _valid_resolution(value: str) -> bool:
    parts = value.lower().split("x")
    return len(parts) == 2 and all(p.isdigit() and 240 <= int(p) <= 4096 for p in parts)


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    if not path.exists():
        return AppConfig()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Не удалось прочитать %s (%s), использую настройки по умолчанию", path, exc)
        return AppConfig()
    if not isinstance(raw, dict):
        return AppConfig()
    known = {f.name: f.type for f in fields(AppConfig)}
    defaults = AppConfig()
    kwargs = {}
    for key, value in raw.items():
        if key not in known:
            continue
        expected = type(getattr(defaults, key))
        if expected is float and isinstance(value, int):
            value = float(value)
        if isinstance(value, expected) and not (expected is int and isinstance(value, bool)):
            kwargs[key] = value
    return validate(AppConfig(**kwargs))


def save_config(cfg: AppConfig, path: Path = CONFIG_PATH) -> None:
    try:
        path.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        log.error("Не удалось сохранить настройки в %s: %s", path, exc)
