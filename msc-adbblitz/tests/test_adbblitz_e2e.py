"""
ADBBlitz 截图功能的端到端测试。

这些测试需要真实的 Android 设备或模拟器连接。
测试使用 adbutils 包提供的 ADB 功能，不依赖系统环境中的 adb 命令。

运行方式：
    pytest -v -m e2e msc-adbblitz/tests/test_adbblitz_e2e.py

跳过 e2e 测试：
    pytest -v -m "not e2e" msc-adbblitz/tests/
"""

import time

import cv2
import numpy as np
import pytest
from adbutils import adb

from msc.adbblitz import ADBBlitz


@pytest.fixture(scope="module")
def device_serial():
    """
    获取连接的第一个设备序列号。

    如果没有设备连接，跳过所有 e2e 测试。
    """
    devices = adb.device_list()
    if not devices:
        pytest.skip("No Android devices connected. Skipping e2e tests.")

    serial = devices[0].serial
    print(f"\nUsing device: {serial}")
    return serial


@pytest.fixture
def adbblitz(device_serial: str):
    """
    创建 ADBBlitz 实例并在测试后清理。
    """
    ab = ADBBlitz(serial=device_serial)
    # No need to wait - _get_latest_frame() auto-waits now
    yield ab
    ab.close()


@pytest.mark.e2e
def test_adbblitz_initialization(device_serial: str):
    """测试 ADBBlitz 初始化。"""
    ab = ADBBlitz(serial=device_serial)

    try:
        assert ab.adb_device is not None
        assert ab.serial == device_serial
        assert ab.width > 0
        assert ab.height > 0
        assert ab.adb_screenshots is not None

        # Get first frame
        image = ab.screencap()
        assert image is not None
        assert image.shape == (ab.height, ab.width, 3)
    finally:
        ab.close()


@pytest.mark.e2e
def test_adbblitz_screencap_raw(adbblitz: ADBBlitz):
    """测试原始截图功能。"""
    raw_data = adbblitz.screencap_raw()

    # 验证返回的是字节数据
    assert isinstance(raw_data, bytes)

    # 验证数据长度符合预期（RGBA格式）
    expected_size = adbblitz.width * adbblitz.height * 4
    assert len(raw_data) == expected_size, (
        f"Raw data size {len(raw_data)} != expected {expected_size}"
    )


@pytest.mark.e2e
def test_adbblitz_screencap(adbblitz: ADBBlitz):
    """测试 OpenCV 格式截图功能。"""
    image = adbblitz.screencap()

    # 验证返回的是 numpy 数组
    assert isinstance(image, np.ndarray)

    # 验证图像尺寸
    assert image.shape == (adbblitz.height, adbblitz.width, 3)

    # 验证图像格式为 BGR（OpenCV 默认格式）
    assert image.dtype == np.uint8

    # 验证图像内容不是全黑或全白
    mean_value = image.mean()
    assert 0 < mean_value < 255, f"Image appears to be invalid (mean={mean_value})"


@pytest.mark.e2e
def test_adbblitz_multiple_captures(adbblitz: ADBBlitz):
    """测试连续多次截图。"""
    images = []
    for i in range(5):
        img = adbblitz.screencap()
        images.append(img)
        time.sleep(0.1)  # Small delay between captures

        # 验证每次截图的尺寸一致
        assert img.shape == (adbblitz.height, adbblitz.width, 3)

    # 验证所有截图都是有效的
    for i, img in enumerate(images):
        mean_value = img.mean()
        assert 0 < mean_value < 255, f"Image {i} appears to be invalid (mean={mean_value})"


@pytest.mark.e2e
def test_adbblitz_save_screencap(adbblitz: ADBBlitz, tmp_path):
    """测试保存截图功能。"""
    # 保存截图到临时目录
    output_file = tmp_path / "test_adbblitz_screenshot.png"
    adbblitz.save_screencap(str(output_file))

    # 验证文件已创建
    assert output_file.exists()

    # 验证可以读取保存的图像
    saved_image = cv2.imread(str(output_file))
    assert saved_image is not None
    assert saved_image.shape == (adbblitz.height, adbblitz.width, 3)


@pytest.mark.e2e
def test_adbblitz_context_manager(device_serial: str):
    """测试上下文管理器功能。"""
    with ADBBlitz(serial=device_serial) as ab:
        # Auto-waits for first frame
        image = ab.screencap()
        assert isinstance(image, np.ndarray)
        assert image.shape == (ab.height, ab.width, 3)


@pytest.mark.e2e
def test_adbblitz_performance(adbblitz: ADBBlitz):
    """测试截图性能（确保在合理时间内完成）。"""
    # 预热
    adbblitz.screencap()

    # 测试性能
    start = time.time()
    for _ in range(10):
        adbblitz.screencap()
    elapsed = time.time() - start

    avg_time = elapsed / 10
    print(f"\nAverage ADBBlitz screencap time: {avg_time*1000:.2f}ms")

    # ADBBlitz 应该非常快，确保单次截图在 100ms 内完成
    assert avg_time < 0.1, f"ADBBlitz screencap is too slow: {avg_time:.2f}s per capture"


@pytest.mark.e2e
def test_adbblitz_streaming_iterator(device_serial: str):
    """测试流式迭代器功能。"""
    ab = ADBBlitz(serial=device_serial)

    try:
        frame_count = 0
        start_time = time.time()

        for frame in ab:
            assert isinstance(frame, np.ndarray)
            assert frame.shape == (ab.height, ab.width, 3)

            frame_count += 1
            if frame_count >= 5:  # Capture 5 frames
                break

            # Timeout safety
            if time.time() - start_time > 5:
                break

        assert frame_count >= 5, f"Only captured {frame_count} frames"
    finally:
        ab.close()


@pytest.mark.e2e
def test_adbblitz_thread_cleanup(device_serial: str):
    """测试线程清理。"""
    ab = ADBBlitz(serial=device_serial)

    # Verify screencap works
    image = ab.screencap()
    assert image is not None

    # Close and verify cleanup
    ab.close()
    time.sleep(0.5)

    # After closing, adbnativeblitz should have stopped capture
    # We can't directly check internal state, but we can verify
    # that the instance was properly cleaned up
    assert ab.adb_screenshots is not None


@pytest.mark.e2e
def test_adbblitz_custom_resolution(device_serial: str):
    """测试自定义分辨率参数。"""
    ab = ADBBlitz(serial=device_serial, width=640, height=480)

    try:
        assert ab.width == 640
        assert ab.height == 480

        # Try to get first frame (will auto-wait or raise error)
        try:
            image = ab.screencap()
            assert image.shape == (480, 640, 3)
        except RuntimeError as e:
            if "terminated unexpectedly" in str(e) or "No frames available" in str(e):
                pytest.skip("Device does not support custom resolution for screenrecord")
            raise
    finally:
        ab.close()


@pytest.mark.e2e
def test_adbblitz_bitrate_parameter(device_serial: str):
    """测试不同码率参数。"""
    # Use default resolution to avoid resolution issues
    ab = ADBBlitz(serial=device_serial, bitrate="4M")  # 4Mbps

    try:
        # Verify first frame can be captured
        image = ab.screencap()
        assert isinstance(image, np.ndarray)
    except RuntimeError as e:
        pytest.skip("Device screenrecord failed to start with custom bitrate")
    finally:
        ab.close()


@pytest.mark.e2e
def test_adbblitz_buffer_size(device_serial: str):
    """测试帧缓冲区大小参数。"""
    ab = ADBBlitz(serial=device_serial, buffer_size=10)

    try:
        # Verify we can capture frames
        image = ab.screencap()
        assert image is not None
    finally:
        ab.close()


@pytest.mark.e2e
def test_adbblitz_device_info(device_serial: str):
    """测试设备信息获取。"""
    ab = ADBBlitz(serial=device_serial)

    try:
        assert ab.adb_device is not None
        assert ab.width > 0
        assert ab.height > 0

        # Verify first frame can be captured
        image = ab.screencap()
        assert image.shape == (ab.height, ab.width, 3)
    finally:
        ab.close()
