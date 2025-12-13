"""
ADBBlitz 的单元测试（使用 mocking）。

运行方式:
    pytest -v -m unit msc-adbblitz/tests/test_adbblitz_unit.py
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from msc.adbblitz import ADBBlitz


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_init_parameters(mock_adb, mock_adbnativeblitz):
    """测试初始化参数处理。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz
    mock_screenshots = Mock()
    mock_adbnativeblitz.return_value = mock_screenshots

    # Create instance with custom parameters
    ab = ADBBlitz(
        serial="test_serial",
        time_interval=100,
        width=1280,
        height=720,
        bitrate="4M",
        buffer_size=20,
        go_idle=0.01,
    )

    # Verify parameters
    assert ab.serial == "test_serial"
    assert ab.width == 1280
    assert ab.height == 720

    # Verify AdbFastScreenshots was called with correct parameters
    call_kwargs = mock_adbnativeblitz.call_args[1]
    assert call_kwargs["device_serial"] == "test_serial"
    assert call_kwargs["time_interval"] == 100
    assert call_kwargs["width"] == 1280
    assert call_kwargs["height"] == 720
    assert call_kwargs["bitrate"] == "4M"
    assert call_kwargs["screenshotbuffer"] == 20
    assert call_kwargs["go_idle"] == 0.01

    ab.close()


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_default_resolution(mock_adb, mock_adbnativeblitz):
    """测试默认分辨率使用设备尺寸。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz
    mock_screenshots = Mock()
    mock_adbnativeblitz.return_value = mock_screenshots

    # Create instance without specifying resolution
    ab = ADBBlitz(serial="test_serial")

    # Should use device resolution
    assert ab.width == 1920
    assert ab.height == 1080

    # Verify AdbFastScreenshots was called with device resolution
    call_kwargs = mock_adbnativeblitz.call_args[1]
    assert call_kwargs["width"] == 1920
    assert call_kwargs["height"] == 1080

    ab.close()


@pytest.mark.unit
def test_adbblitz_frame_buffer_management():
    """测试帧缓冲区管理（仅测试缓冲区逻辑）。"""
    # This test is about deque behavior, which is independent of ADBBlitz
    from collections import deque

    buffer = deque(maxlen=5)

    # Add frames
    for i in range(10):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :, 0] = i  # Mark frame with index
        buffer.append(frame)

    # Should only keep last 5 frames
    assert len(buffer) == 5

    # Verify oldest frames were dropped
    assert buffer[0][0, 0, 0] == 5
    assert buffer[-1][0, 0, 0] == 9


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_screencap(mock_adb, mock_adbnativeblitz):
    """测试 screencap() 获取帧。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (100, 100)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz instance
    mock_screenshots = Mock()
    test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    test_frame[:, :, 0] = 255  # Blue channel

    # Mock iterator
    mock_screenshots.__iter__ = Mock(return_value=iter([test_frame]))
    mock_adbnativeblitz.return_value = mock_screenshots

    ab = ADBBlitz(serial="test_serial")

    # Get frame
    frame = ab.screencap()

    # Verify frame is returned
    assert frame is not None
    assert frame.shape == (100, 100, 3)
    assert frame[0, 0, 0] == 255

    ab.close()


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_screencap_raw_conversion(mock_adb, mock_adbnativeblitz):
    """测试 screencap_raw 的格式转换。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (100, 100)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz instance
    mock_screenshots = Mock()
    test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    test_frame[:, :, 2] = 255  # Red channel in BGR

    # Mock iterator to return test frame
    mock_screenshots.__iter__ = Mock(return_value=iter([test_frame]))
    mock_adbnativeblitz.return_value = mock_screenshots

    ab = ADBBlitz(serial="test_serial")

    # Get raw data
    raw_data = ab.screencap_raw()

    # Should be RGBA format
    assert len(raw_data) == 100 * 100 * 4

    # Verify conversion (BGR -> RGBA)
    raw_array = np.frombuffer(raw_data, dtype=np.uint8).reshape((100, 100, 4))
    assert raw_array[0, 0, 0] == 255  # Red channel
    assert raw_array[0, 0, 3] == 255  # Alpha channel

    ab.close()


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_iterator(mock_adb, mock_adbnativeblitz):
    """测试迭代器功能。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (100, 100)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz instance
    mock_screenshots = Mock()
    frames = [
        np.zeros((100, 100, 3), dtype=np.uint8),
        np.ones((100, 100, 3), dtype=np.uint8),
    ]

    # Mock iterator
    mock_screenshots.__iter__ = Mock(return_value=iter(frames))
    mock_adbnativeblitz.return_value = mock_screenshots

    ab = ADBBlitz(serial="test_serial")

    # Iterate and collect frames
    collected_frames = list(ab)

    # Verify we got the frames
    assert len(collected_frames) == 2
    assert np.array_equal(collected_frames[0], frames[0])
    assert np.array_equal(collected_frames[1], frames[1])

    ab.close()


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_close_cleanup(mock_adb, mock_adbnativeblitz):
    """测试 close() 方法的资源清理。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz instance
    mock_screenshots = Mock()
    mock_adbnativeblitz.return_value = mock_screenshots

    ab = ADBBlitz(serial="test_serial")

    # Close
    ab.close()

    # Verify cleanup
    mock_screenshots.stop_capture.assert_called_once()


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_context_manager(mock_adb, mock_adbnativeblitz):
    """测试上下文管理器功能。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (100, 100)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz instance
    mock_screenshots = Mock()
    test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_screenshots.__iter__ = Mock(return_value=iter([test_frame]))
    mock_adbnativeblitz.return_value = mock_screenshots

    # Use as context manager
    with ADBBlitz(serial="test_serial") as ab:
        frame = ab.screencap()
        assert frame is not None

    # Verify cleanup was called
    mock_screenshots.stop_capture.assert_called_once()


@pytest.mark.unit
@patch("msc.adbblitz.AdbFastScreenshots")
@patch("msc.adbblitz.adb")
def test_adbblitz_screencap_stop_iteration(mock_adb, mock_adbnativeblitz):
    """测试当迭代器停止时的错误处理。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (100, 100)
    mock_adb.device.return_value = mock_device

    # Mock adbnativeblitz instance with empty iterator
    mock_screenshots = Mock()
    mock_screenshots.__iter__ = Mock(return_value=iter([]))
    mock_adbnativeblitz.return_value = mock_screenshots

    ab = ADBBlitz(serial="test_serial")

    # Should raise RuntimeError when no frames available
    with pytest.raises(RuntimeError, match="Frame capture has stopped"):
        ab.screencap()

    ab.close()
