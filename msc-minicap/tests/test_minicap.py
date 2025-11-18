from types import SimpleNamespace

import numpy as np
import pytest

from msc.minicap import MiniCap, MiniCapStream


class _FakeSocket:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def connect(self, addr) -> None:  # noqa: ARG002
        # No-op for tests
        return None

    def recv(self, bufsize: int) -> bytes:  # noqa: ARG002
        if self._chunks:
            return self._chunks.pop(0)
        return b""


def _make_minicap_stream_chunk(width: int, height: int) -> bytes:
    # Build a minimal banner with virtualWidth/virtualHeight set.
    banner = bytearray(24)
    banner[0] = 1  # version
    banner[1] = 24  # length

    # virtualWidth at bytes 14..17 (little-endian)
    vw = width
    banner[14] = vw & 0xFF
    banner[15] = (vw >> 8) & 0xFF
    banner[16] = (vw >> 16) & 0xFF
    banner[17] = (vw >> 24) & 0xFF

    # virtualHeight at bytes 18..21 (little-endian)
    vh = height
    banner[18] = vh & 0xFF
    banner[19] = (vh >> 8) & 0xFF
    banner[20] = (vh >> 16) & 0xFF
    banner[21] = (vh >> 24) & 0xFF

    # A single RGBA frame of solid color (width x height)
    rgba = bytes([10, 20, 30, 255]) * (width * height)
    return bytes(banner) + rgba


def test_minicap_stream_reads_single_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    width, height = 2, 1
    chunk = _make_minicap_stream_chunk(width, height)

    fake_socket = _FakeSocket([chunk, b""])

    stream = MiniCapStream("127.0.0.1", 12345)
    # Bypass real socket creation
    stream.sock = fake_socket  # type: ignore[assignment]

    # Run in current thread; no need to call start()
    stream.read_stream()

    assert stream.data is not None
    assert len(stream.data) == width * height * 4


def test_minicap_screencap_stream_rgba_to_bgr(monkeypatch: pytest.MonkeyPatch) -> None:
    width, height = 2, 1
    pixels = np.array(
        [[[10, 20, 30, 255], [40, 50, 60, 255]]], dtype=np.uint8
    )  # (1, 2, 4)
    raw_bytes = pixels.tobytes()

    # Build a bare MiniCap instance without running __init__
    cap = MiniCap.__new__(MiniCap)  # type: ignore[call-arg]
    cap.width = width
    cap.height = height
    cap.buffer_size = width * height * 4
    cap.use_stream = True

    # Ensure screencap_raw returns our fake buffer
    monkeypatch.setattr(MiniCap, "screencap_raw", lambda self: raw_bytes)

    mat = MiniCap.screencap(cap)
    assert mat.shape == (height, width, 3)

    # BGR order
    assert mat[0, 0].tolist() == [30, 20, 10]
    assert mat[0, 1].tolist() == [60, 50, 40]

