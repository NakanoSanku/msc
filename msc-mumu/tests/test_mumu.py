import ctypes
from typing import Any

import numpy as np
import pytest

from msc import mumu as mumu_module
from msc.mumu import MuMuCap


class FakeMuMuApi:
    def __init__(self, dll_path: str) -> None:  # noqa: ARG002
        self.connected = False
        self.disconnected_handle: Any | None = None
        self.width = 2
        self.height = 1

    def connect(self, install_path: str, instance_index: int) -> int:  # noqa: ARG002
        self.connected = True
        return 123  # fake handle

    def capture_display(
        self,
        handle: int,  # noqa: ARG002
        display_id: int,  # noqa: ARG002
        buffer_size: int,
        width,
        height,
        pixels,
    ) -> int:
        # 第一次调用：MuMuCap.__get_display_info 获取宽高
        if buffer_size == 0 and pixels is None:
            # width / height 是 ctypes.byref 传入的指针包装对象
            ctypes.cast(width, ctypes.POINTER(ctypes.c_int)).contents.value = self.width
            ctypes.cast(height, ctypes.POINTER(ctypes.c_int)).contents.value = self.height
            return 0

        # 第二次调用：MuMuCap.screencap 填充像素缓存
        assert buffer_size == self.width * self.height * 4
        # pixels 是 ctypes.c_ubyte 数组
        rgba = np.array(
            [[[10, 20, 30, 255], [40, 50, 60, 255]]],
            dtype=np.uint8,
        ).tobytes()
        for i, b in enumerate(rgba):
            pixels[i] = b
        return 0

    def disconnect(self, handle: int) -> None:
        self.disconnected_handle = handle


def test_mumucap_screencap_converts_rgba_to_bgr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 让 get_mumu_path 返回一个虚拟路径
    monkeypatch.setattr(mumu_module, "get_mumu_path", lambda: "C:/fake/mumu")

    real_exists = mumu_module.os.path.exists

    def fake_exists(path: str) -> bool:
        if path.endswith("uninstall.exe") or path.endswith("external_renderer_ipc.dll"):
            return True
        return real_exists(path)

    monkeypatch.setattr(mumu_module.os.path, "exists", fake_exists)
    monkeypatch.setattr(mumu_module, "MuMuApi", FakeMuMuApi)

    cap = MuMuCap(instance_index=0)

    assert cap.width == 2
    assert cap.height == 1
    assert cap.buffer_size == 2 * 1 * 4

    mat = cap.screencap()
    assert mat.shape == (1, 2, 3)

    # BGR 顺序，且 `__buffer2opencv` 会垂直翻转
    assert mat[0, 0].tolist() == [30, 20, 10]
    assert mat[0, 1].tolist() == [60, 50, 40]


def test_mumucap_disconnect_on_del(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mumu_module, "get_mumu_path", lambda: "C:/fake/mumu")
    real_exists = mumu_module.os.path.exists

    def fake_exists(path: str) -> bool:
        if path.endswith("uninstall.exe") or path.endswith("external_renderer_ipc.dll"):
            return True
        return real_exists(path)

    monkeypatch.setattr(mumu_module.os.path, "exists", fake_exists)

    fake_api = FakeMuMuApi("dummy.dll")
    monkeypatch.setattr(mumu_module, "MuMuApi", lambda dll_path: fake_api)

    cap = MuMuCap(instance_index=0)
    handle = cap.handle

    # 显式调用析构方法，验证 disconnect 被调用
    cap.__del__()

    assert fake_api.disconnected_handle == handle
