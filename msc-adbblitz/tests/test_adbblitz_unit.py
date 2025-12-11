"""
ADBBlitz 的单元测试（使用 mocking）。

运行方式：
    pytest -v -m unit msc-adbblitz/tests/test_adbblitz_unit.py
"""

from collections import deque
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from msc.adbblitz import ADBBlitz


@pytest.mark.unit
@patch("msc.adbblitz.adb")
@patch("msc.adbblitz.subprocess.Popen")
@patch("msc.adbblitz.av")
def test_adbblitz_init_parameters(mock_av, mock_popen, mock_adb):
    """测试初始化参数处理。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock codec
    mock_av.codec.CodecContext.create.return_value = Mock()

    # Mock process
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_popen.return_value = mock_process

    # Create instance with custom parameters
    with patch.object(ADBBlitz, "_start_capture"):
        ab = ADBBlitz(
            serial="test_serial",
            time_interval=10.0,
            width=1280,
            height=720,
            bitrate=4000000,
            buffer_size=20,
        )

        # Verify parameters
        assert ab.adb.serial == "test_serial"
        assert ab.time_interval == 10.0
        assert ab.width == 1280
        assert ab.height == 720
        assert ab.bitrate == 4000000
        assert ab.buffer_size == 20


@pytest.mark.unit
@patch("msc.adbblitz.adb_path")
@patch("msc.adbblitz.adb")
@patch("msc.adbblitz.subprocess.Popen")
@patch("msc.adbblitz.av")
def test_adbblitz_command_construction(mock_av, mock_popen, mock_adb, mock_adb_path):
    """测试 screenrecord 命令构造。"""
    # Mock adb_path
    mock_adb_path.return_value = "/usr/bin/adb"

    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock codec
    mock_av.codec.CodecContext.create.return_value = Mock()

    # Mock process
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_popen.return_value = mock_process

    # Create instance
    ab = ADBBlitz(serial="test_serial", width=1280, height=720, bitrate=5000000)

    # Verify Popen was called with correct command
    call_args = mock_popen.call_args
    cmd_parts = call_args[0][0]

    assert "screenrecord" in cmd_parts
    assert "--output-format=h264" in cmd_parts
    assert "--bit-rate=5000000" in cmd_parts
    assert "--size=1280x720" in cmd_parts
    assert "-" in cmd_parts  # stdout

    ab.close()


@pytest.mark.unit
def test_adbblitz_frame_buffer_management():
    """测试帧缓冲区管理。"""
    # Test deque with maxlen
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
@patch("msc.adbblitz.adb")
@patch("msc.adbblitz.subprocess.Popen")
@patch("msc.adbblitz.av")
def test_adbblitz_get_latest_frame_error(mock_av, mock_popen, mock_adb):
    """测试在没有帧时获取帧的错误。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock codec
    mock_av.codec.CodecContext.create.return_value = Mock()

    # Mock process
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_popen.return_value = mock_process

    # Mock thread that is alive
    mock_thread = Mock()
    mock_thread.is_alive.return_value = True

    with patch.object(ADBBlitz, "_start_capture"):
        ab = ADBBlitz(serial="test_serial")
        ab.capture_thread = mock_thread  # Set mock thread

        # Clear buffer
        ab.frame_buffer.clear()

        # Should raise error after timeout (with shorter timeout for testing)
        with pytest.raises(RuntimeError, match="No frames available after"):
            ab._get_latest_frame(timeout=0.1)  # Use short timeout

        ab.close()


@pytest.mark.unit
@patch("msc.adbblitz.adb")
@patch("msc.adbblitz.subprocess.Popen")
@patch("msc.adbblitz.av")
def test_adbblitz_screencap_raw_conversion(mock_av, mock_popen, mock_adb):
    """测试 screencap_raw 的格式转换。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (100, 100)
    mock_adb.device.return_value = mock_device

    # Mock codec
    mock_av.codec.CodecContext.create.return_value = Mock()

    # Mock process
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_popen.return_value = mock_process

    with patch.object(ADBBlitz, "_start_capture"):
        ab = ADBBlitz(serial="test_serial")

        # Add a test frame (BGR format)
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        test_frame[:, :, 2] = 255  # Red channel in BGR
        ab.frame_buffer.append(test_frame)

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
@patch("msc.adbblitz.adb")
@patch("msc.adbblitz.subprocess.Popen")
@patch("msc.adbblitz.av")
def test_adbblitz_close_cleanup(mock_av, mock_popen, mock_adb):
    """测试 close() 方法的资源清理。"""
    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock codec
    mock_av.codec.CodecContext.create.return_value = Mock()

    # Mock process
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process running
    mock_process.stdout = Mock()
    mock_popen.return_value = mock_process

    # Mock thread
    mock_thread = Mock()
    mock_thread.is_alive.return_value = True

    with patch.object(ADBBlitz, "_start_capture"):
        ab = ADBBlitz(serial="test_serial")
        ab.process = mock_process  # Set the process
        ab.capture_thread = mock_thread

        # Close
        ab.close()

        # Verify cleanup
        assert ab.stop_event.is_set()
        mock_process.terminate.assert_called_once()
        mock_thread.join.assert_called_once()
        assert len(ab.frame_buffer) == 0


@pytest.mark.unit
@patch("msc.adbblitz.platform.system")
@patch("msc.adbblitz.adb_path")
@patch("msc.adbblitz.adb")
@patch("msc.adbblitz.subprocess.Popen")
@patch("msc.adbblitz.av")
def test_adbblitz_windows_subprocess_config(mock_av, mock_popen, mock_adb, mock_adb_path, mock_platform):
    """测试 Windows 平台的子进程配置。"""
    # Mock Windows platform
    mock_platform.return_value = "Windows"

    # Mock adb_path
    mock_adb_path.return_value = "/usr/bin/adb"

    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock codec
    mock_av.codec.CodecContext.create.return_value = Mock()

    # Mock process
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_popen.return_value = mock_process

    # Mock subprocess Windows-only attributes
    with patch("msc.adbblitz.subprocess.STARTUPINFO", create=True) as mock_startupinfo_class:
        with patch("msc.adbblitz.subprocess.STARTF_USESHOWWINDOW", 1, create=True):
            with patch("msc.adbblitz.subprocess.SW_HIDE", 0, create=True):
                with patch("msc.adbblitz.subprocess.CREATE_NO_WINDOW", 0x08000000, create=True):
                    # Create instance
                    ab = ADBBlitz(serial="test_serial")

                    # Verify startupinfo was created
                    mock_startupinfo_class.assert_called_once()

                    # Verify Popen was called
                    assert mock_popen.called

                    ab.close()


@pytest.mark.unit
@patch("msc.adbblitz.platform.system")
@patch("msc.adbblitz.adb_path")
@patch("msc.adbblitz.adb")
@patch("msc.adbblitz.subprocess.Popen")
@patch("msc.adbblitz.av")
def test_adbblitz_linux_subprocess_config(mock_av, mock_popen, mock_adb, mock_adb_path, mock_platform):
    """测试 Linux 平台的子进程配置。"""
    # Mock Linux platform
    mock_platform.return_value = "Linux"

    # Mock adb_path
    mock_adb_path.return_value = "/usr/bin/adb"

    # Mock device
    mock_device = Mock()
    mock_device.serial = "test_serial"
    mock_device.window_size.return_value = (1920, 1080)
    mock_adb.device.return_value = mock_device

    # Mock codec
    mock_av.codec.CodecContext.create.return_value = Mock()

    # Mock process
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_popen.return_value = mock_process

    # Create instance
    ab = ADBBlitz(serial="test_serial")

    # Verify Popen was called without Windows-specific parameters
    call_kwargs = mock_popen.call_args[1]
    assert call_kwargs["startupinfo"] is None
    assert call_kwargs["creationflags"] == 0

    ab.close()
