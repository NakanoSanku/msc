import time
from typing import Any

import numpy as np
import pytest
import requests

from msc.droidcast import DroidCast


def test_droidcast_screencap_converts_rgba_to_bgr(monkeypatch: pytest.MonkeyPatch) -> None:
    width, height = 2, 1
    # RGBA pixels
    pixels = np.array(
        [[[10, 20, 30, 255], [40, 50, 60, 255]]],
        dtype=np.uint8,
    )
    raw = pixels.tobytes()

    dc = DroidCast.__new__(DroidCast)  # type: ignore[call-arg]
    dc.width = width
    dc.height = height
    dc.buffer_size = width * height * 4

    # screencap_raw 应该返回 RGBA 缓冲
    monkeypatch.setattr(DroidCast, "screencap_raw", lambda self: raw)

    mat = DroidCast.screencap(dc)

    assert mat.shape == (height, width, 3)
    # BGR 顺序
    assert mat[0, 0].tolist() == [30, 20, 10]
    assert mat[0, 1].tolist() == [60, 50, 40]


def test_droidcast_screencap_raw_retries_and_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    dc = DroidCast.__new__(DroidCast)  # type: ignore[call-arg]
    dc.url = "http://127.0.0.1:12345"
    dc.timeout = 0.1

    class FakeSession:
        def get(self, url: str, timeout: float) -> Any:  # noqa: ARG002
            raise requests.exceptions.ConnectionError("connection failed")

    restart_calls: list[float] = []

    def fake_restart(self) -> None:
        restart_calls.append(time.time())

    dc.session = FakeSession()

    # 减少测试时间
    monkeypatch.setattr(DroidCast, "MAX_RETRY", 2)
    monkeypatch.setattr(DroidCast, "RETRY_DELAY", 0.0)
    monkeypatch.setattr(DroidCast, "restart", fake_restart, raising=False)

    with pytest.raises(RuntimeError) as exc:
        DroidCast.screencap_raw(dc)

    assert "Failed to get screenshot from DroidCast" in str(exc.value)
    # 应该重试多次
    assert len(restart_calls) == 2
