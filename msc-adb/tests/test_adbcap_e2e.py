"""
ADB 截图功能的端到端测试。

这些测试需要真实的 Android 设备或模拟器连接。
测试使用 adbutils 包提供的 ADB 功能，不依赖系统环境中的 adb 命令。

运行方式：
    pytest -v -m e2e msc-adb/tests/test_adbcap_e2e.py

跳过 e2e 测试：
    pytest -v -m "not e2e" msc-adb/tests/
"""

import cv2
import numpy as np
import pytest
from adbutils import adb

from msc.adbcap import ADBCap


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


@pytest.mark.e2e
def test_adbcap_initialization(device_serial: str):
    """测试 ADBCap 初始化。"""
    cap = ADBCap(serial=device_serial)

    assert cap.adb is not None
    assert cap.adb.serial == device_serial
    assert cap.width > 0
    assert cap.height > 0
    assert cap.buffer_size == cap.width * cap.height * 4


@pytest.mark.e2e
def test_adbcap_screencap_raw(device_serial: str):
    """测试原始截图功能。"""
    cap = ADBCap(serial=device_serial)
    raw_data = cap.screencap_raw()

    # 验证返回的是字节数据
    assert isinstance(raw_data, bytes)

    # 验证数据长度符合预期（RGBA格式）
    expected_size = cap.width * cap.height * 4
    assert len(raw_data) >= expected_size, (
        f"Raw data size {len(raw_data)} is less than expected {expected_size}"
    )


@pytest.mark.e2e
def test_adbcap_screencap(device_serial: str):
    """测试 OpenCV 格式截图功能。"""
    cap = ADBCap(serial=device_serial)
    image = cap.screencap()

    # 验证返回的是 numpy 数组
    assert isinstance(image, np.ndarray)

    # 验证图像尺寸
    assert image.shape == (cap.height, cap.width, 3)

    # 验证图像格式为 BGR（OpenCV 默认格式）
    assert image.dtype == np.uint8

    # 验证图像内容不是全黑或全白（基本的合理性检查）
    mean_value = image.mean()
    assert 0 < mean_value < 255, (
        f"Image appears to be invalid (mean={mean_value})"
    )


@pytest.mark.e2e
def test_adbcap_multiple_captures(device_serial: str):
    """测试连续多次截图。"""
    cap = ADBCap(serial=device_serial)

    images = []
    for i in range(3):
        img = cap.screencap()
        images.append(img)

        # 验证每次截图的尺寸一致
        assert img.shape == (cap.height, cap.width, 3)

    # 验证所有截图都是有效的
    for i, img in enumerate(images):
        mean_value = img.mean()
        assert 0 < mean_value < 255, (
            f"Image {i} appears to be invalid (mean={mean_value})"
        )


@pytest.mark.e2e
def test_adbcap_save_screencap(device_serial: str, tmp_path):
    """测试保存截图功能。"""
    cap = ADBCap(serial=device_serial)

    # 保存截图到临时目录
    output_file = tmp_path / "test_screenshot.png"
    cap.save_screencap(str(output_file))

    # 验证文件已创建
    assert output_file.exists()

    # 验证可以读取保存的图像
    saved_image = cv2.imread(str(output_file))
    assert saved_image is not None
    assert saved_image.shape == (cap.height, cap.width, 3)


@pytest.mark.e2e
def test_adbcap_with_display_id(device_serial: str):
    """测试指定显示器 ID 的截图功能。"""
    # 默认使用 display_id=0
    cap = ADBCap(serial=device_serial, display_id=0)
    image = cap.screencap()

    assert isinstance(image, np.ndarray)
    assert image.shape == (cap.height, cap.width, 3)


@pytest.mark.e2e
def test_adbcap_context_manager(device_serial: str):
    """测试上下文管理器功能。"""
    with ADBCap(serial=device_serial) as cap:
        image = cap.screencap()
        assert isinstance(image, np.ndarray)
        assert image.shape == (cap.height, cap.width, 3)


@pytest.mark.e2e
def test_adbcap_performance(device_serial: str):
    """测试截图性能（确保在合理时间内完成）。"""
    import time

    cap = ADBCap(serial=device_serial)

    # 预热
    cap.screencap()

    # 测试性能
    start = time.time()
    for _ in range(5):
        cap.screencap()
    elapsed = time.time() - start

    avg_time = elapsed / 5
    print(f"\nAverage screencap time: {avg_time*1000:.2f}ms")

    # 确保单次截图在 5 秒内完成（非常宽松的限制）
    assert avg_time < 5.0, (
        f"Screencap is too slow: {avg_time:.2f}s per capture"
    )


@pytest.mark.e2e
def test_adbcap_invalid_serial():
    """测试使用无效设备序列号的情况。"""
    # 使用一个不存在的设备序列号
    with pytest.raises(Exception):
        cap = ADBCap(serial="invalid-device-serial-12345")
        cap.screencap()
