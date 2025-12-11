import subprocess
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from msc import adbcap
from msc.adbcap import ADBCap, _run_adb_command

pytestmark = pytest.mark.unit


class _CompletedProcess:
    def __init__(self, returncode=0, stdout=b"", stderr=b"") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_adb_command_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command, stdout, stderr, timeout, check):  # type: ignore[override]
        assert command == ["adb", "test"]
        return _CompletedProcess(returncode=0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = _run_adb_command(["adb", "test"], timeout=1.0)
    assert out == b"ok"


def test_run_adb_command_non_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command, stdout, stderr, timeout, check):  # type: ignore[override]
        return _CompletedProcess(returncode=1, stdout=b"", stderr=b"error message")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc:
        _run_adb_command(["adb", "test"], timeout=1.0)
    assert "exit code 1" in str(exc.value)
    assert "error message" in str(exc.value)


def test_run_adb_command_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command, stdout, stderr, timeout, check):  # type: ignore[override]
        raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(subprocess.TimeoutExpired):
        _run_adb_command(["adb", "test"], timeout=0.1)


def test_run_adb_command_no_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command, stdout, stderr, timeout, check):  # type: ignore[override]
        return _CompletedProcess(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc:
        _run_adb_command(["adb", "test"], timeout=1.0)
    assert "no output" in str(exc.value)


def test_adbcap_screencap_converts_rgba_to_bgr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    width, height = 2, 1

    # RGBA pixels: (R, G, B, A)
    pixels = np.array(
        [[[10, 20, 30, 255], [40, 50, 60, 255]]], dtype=np.uint8
    )  # shape (1, 2, 4)
    raw_bytes = pixels.tobytes()

    class DummyDevice:
        def __init__(self, serial: str) -> None:
            self.serial = serial

        def window_size(self) -> tuple[int, int]:
            return width, height

    def fake_device(serial: str) -> DummyDevice:
        return DummyDevice(serial)

    # Patch adb and adb_path used in the module
    monkeypatch.setattr(adbcap, "adb", SimpleNamespace(device=fake_device))
    monkeypatch.setattr(adbcap, "adb_path", lambda: "adb")

    # Patch _run_adb_command to return our fake RGBA buffer
    monkeypatch.setattr(adbcap, "_run_adb_command", lambda cmd, timeout=10.0: raw_bytes)

    cap = ADBCap(serial="dummy-serial")
    mat = cap.screencap()

    assert isinstance(mat, np.ndarray)
    assert mat.shape == (height, width, 3)

    # OpenCV BGR order: (B, G, R)
    assert mat[0, 0].tolist() == [30, 20, 10]
    assert mat[0, 1].tolist() == [60, 50, 40]

