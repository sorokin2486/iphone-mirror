"""Тесты конфигурации, аргументов UxPlay и видеоконвейера (без iPhone)."""
from __future__ import annotations

import json
import socket
import time
from fractions import Fraction

import av
import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication, QRectF, QSize
from PySide6.QtGui import QImage

from app.config import AppConfig, load_config, save_config
from app.phone_view import fit_rect
from app.receiver import build_uxplay_args, video_forward_pipeline
from app.video_stream import H264Decoder, LatestFrame, VideoServer


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def make_h264(width=320, height=640, frames=10) -> bytes:
    """Кодирует тестовое видео в сырой H.264 (Annex-B)."""
    for name in ("libx264", "libopenh264", "h264"):
        try:
            enc = av.CodecContext.create(name, "w")
            break
        except Exception:  # noqa: BLE001 - пробуем следующий энкодер
            continue
    else:
        pytest.skip("В сборке PyAV нет H.264-энкодера")
    enc.width, enc.height, enc.pix_fmt = width, height, "yuv420p"
    enc.time_base = Fraction(1, 30)
    enc.framerate = Fraction(30, 1)
    out = bytearray()
    for i in range(frames):
        img = np.full((height, width, 3), (i * 20) % 255, dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(img, format="rgb24").reformat(format="yuv420p")
        frame.pts = i
        for pkt in enc.encode(frame):
            out += bytes(pkt)
    for pkt in enc.encode(None):
        out += bytes(pkt)
    return bytes(out)


# --- config -----------------------------------------------------------------
def test_load_config_returns_defaults_when_file_missing(tmp_path):
    assert load_config(tmp_path / "nope.json") == AppConfig()


def test_load_config_ignores_bad_types_and_unknown_keys(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"scale": "huge", "fps": True, "foo": 1, "device_name": "Мой ПК"}), "utf-8")
    cfg = load_config(path)
    assert cfg.device_name == "Мой ПК"
    assert cfg.scale == AppConfig.scale and cfg.fps == AppConfig.fps


def test_load_config_survives_corrupt_json(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{not json", "utf-8")
    assert load_config(path) == AppConfig()


def test_with_changes_clamps_and_does_not_mutate():
    base = AppConfig()
    changed = base.with_changes(scale=99, video_port=1, max_resolution="abc", model_color="pink")
    assert base.scale == AppConfig.scale
    assert changed.scale == 1.6
    assert changed.video_port == AppConfig.video_port
    assert changed.max_resolution == AppConfig.max_resolution
    assert changed.model_color == "natural"


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "c.json"
    cfg = AppConfig().with_changes(scale=1.0, always_on_top=True, model_color="blue")
    save_config(cfg, path)
    assert load_config(path) == cfg


# --- receiver ---------------------------------------------------------------
def test_build_args_contains_name_and_forward_pipeline():
    cfg = AppConfig(device_name="Test", video_port=50000)
    args = build_uxplay_args(cfg)
    assert args[args.index("-n") + 1] == "Test"
    assert "port=50000" in args[args.index("-vrtp") + 1]
    assert "-as" not in args


def test_build_args_disables_audio():
    args = build_uxplay_args(AppConfig(audio_enabled=False))
    assert args[args.index("-as") + 1] == "0"


def test_forward_pipeline_starts_with_payloader_property():
    # UxPlay подставляет строку сразу после "rtph264pay ", поэтому первым идёт свойство.
    assert video_forward_pipeline(1234).startswith("config-interval=")


# --- geometry ---------------------------------------------------------------
def test_fit_rect_keeps_aspect_and_centers():
    r = fit_rect(QSize(100, 200), QRectF(0, 0, 400, 400))
    assert (r.width(), r.height()) == (200, 400)
    assert r.center().x() == 200


# --- video ------------------------------------------------------------------
def test_latest_frame_notifies_only_once_until_taken():
    lf = LatestFrame()
    a, b = QImage(1, 1, QImage.Format_RGB888), QImage(2, 2, QImage.Format_RGB888)
    assert lf.put(a) is True
    assert lf.put(b) is False
    assert lf.take().width() == 2
    assert lf.put(a) is True


def test_decoder_handles_data_split_into_small_chunks():
    data = make_h264()
    dec = H264Decoder()
    images = []
    for i in range(0, len(data), 997):
        images += dec.feed(data[i:i + 997])
    images += dec.feed(b"")
    assert images, "декодер не выдал ни одного кадра"
    assert (images[0].width(), images[0].height()) == (320, 640)


def test_decoder_handles_unaligned_width_like_real_iphone():
    dec = H264Decoder()
    images = dec.feed(make_h264(width=886, height=1920, frames=3)) + dec.feed(b"")
    assert images and images[0].width() == 886


def test_video_server_receives_stream_over_tcp(qapp):
    port = _free_port()
    server = VideoServer(port)
    events = []
    server.stream_started.connect(lambda: events.append("start"))
    server.stream_ended.connect(lambda: events.append("end"))
    server.start()
    try:
        _send_when_ready(port, make_h264(frames=20))
        deadline = time.time() + 10
        while "end" not in events and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.02)
    finally:
        server.stop()
    assert events[:1] == ["start"] and "end" in events
    assert server.latest.take() is not None


def test_video_server_serves_new_stream_while_idle_connection_is_open(qapp):
    # Так ведёт себя UxPlay: держит пустое соединение открытым с момента запуска.
    port = _free_port()
    server = VideoServer(port)
    events = []
    server.stream_started.connect(lambda: events.append("start"))
    server.stream_ended.connect(lambda: events.append("end"))
    server.start()
    idle = None
    try:
        for _ in range(50):
            try:
                idle = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except ConnectionRefusedError:
                time.sleep(0.05)
        _send_when_ready(port, make_h264(frames=20))
        deadline = time.time() + 10
        while "end" not in events and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.02)
    finally:
        if idle is not None:
            idle.close()
        server.stop()
    assert events == ["start", "end"]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _send_when_ready(port: int, payload: bytes) -> None:
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1) as c:
                c.sendall(payload)
            return
        except ConnectionRefusedError:
            time.sleep(0.05)
    raise RuntimeError("сервер не поднялся")
