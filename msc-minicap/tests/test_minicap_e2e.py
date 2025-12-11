"""
Minicap 截图功能的端到端测试。

这些测试需要真实的 Android 设备或模拟器连接。
测试使用 adbutils 包提供的 ADB 功能，不依赖系统环境中的 adb 命令。

注意：Minicap 仅支持 Android SDK <= 34

运行方式：
    pytest -v -m e2e msc-minicap/tests/test_minicap_e2e.py

跳过 e2e 测试：
    pytest -v -m "not e2e" msc-minicap/tests/
"""

import cv2
import numpy as np
import pytest
from adbutils import adb

from msc.minicap import MiniCap, MiniCapUnSupportError


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


@pytest.fixture(scope="module")
def check_minicap_support(device_serial: str):
    """
    检查设备是否支持 Minicap（SDK <= 34）。
    """
    device = adb.device(device_serial)
    sdk = int(device.getprop("ro.build.version.sdk"))

    if sdk > 34:
        pytest.skip(f"Minicap does not support Android SDK {sdk} (Max 34)")

    return sdk


@pytest.fixture(scope="module")
def minicap(device_serial: str, check_minicap_support):
    """
    创建 MiniCap 实例并在测试后清理。
    使用 module scope 以避免频繁创建销毁导致的端口冲突。
    """
    mc = MiniCap(serial=device_serial, use_stream=True)
    yield mc
    mc.close()


@pytest.mark.e2e
def test_minicap_initialization(device_serial: str, check_minicap_support):
    """测试 Minicap 初始化和安装。"""
    mc = MiniCap(serial=device_serial, use_stream=True)

    try:
        assert mc.adb is not None
        assert mc.adb.serial == device_serial
        assert mc.width > 0
        assert mc.height > 0
        assert mc.buffer_size == mc.width * mc.height * 4
        assert mc.abi is not None
        assert mc.sdk is not None
        assert mc.vm_size is not None
        assert mc.rotation is not None
        assert mc.popen is not None
        assert mc.stream is not None
    finally:
        mc.close()


@pytest.mark.e2e
def test_minicap_sdk_version_check(device_serial: str):
    """测试 SDK 版本检查（SDK > 34 应该抛出异常）。"""
    device = adb.device(device_serial)
    sdk = int(device.getprop("ro.build.version.sdk"))

    if sdk > 34:
        with pytest.raises(MiniCapUnSupportError) as exc:
            MiniCap(serial=device_serial)
        assert "does not support Android SDK" in str(exc.value)
    else:
        # SDK <= 34 应该能正常初始化
        mc = MiniCap(serial=device_serial)
        mc.close()


@pytest.mark.e2e
def test_minicap_screencap_raw_stream(minicap: MiniCap):
    """测试原始截图功能（stream 模式）。"""
    raw_data = minicap.screencap_raw()

    # 验证返回的是字节数据
    assert isinstance(raw_data, bytes)

    # 验证数据长度符合预期（RGBA格式）
    expected_size = minicap.width * minicap.height * 4
    assert len(raw_data) >= expected_size, (
        f"Raw data size {len(raw_data)} is less than expected {expected_size}"
    )


@pytest.mark.e2e
def test_minicap_screencap_stream(minicap: MiniCap):
    """测试 OpenCV 格式截图功能（stream 模式）。"""
    image = minicap.screencap()

    # 验证返回的是 numpy 数组
    assert isinstance(image, np.ndarray)

    # 验证图像尺寸
    assert image.shape == (minicap.height, minicap.width, 3)

    # 验证图像格式为 BGR（OpenCV 默认格式）
    assert image.dtype == np.uint8

    # 验证图像内容不是全黑或全白
    mean_value = image.mean()
    assert 0 < mean_value < 255, (
        f"Image appears to be invalid (mean={mean_value})"
    )


@pytest.mark.e2e
def test_minicap_screencap_non_stream(device_serial: str, check_minicap_support):
    """测试 OpenCV 格式截图功能（非 stream 模式）。

    注意：如果 minicap 被魔改为直接返回 raw 数据而不是 JPEG，
    此测试可能会失败。这是预期行为。
    """
    mc = MiniCap(serial=device_serial, use_stream=False)

    try:
        # 尝试截图
        try:
            image = mc.screencap()

            # 验证返回的是 numpy 数组
            assert isinstance(image, np.ndarray)

            # 验证图像尺寸
            assert image.shape == (mc.height, mc.width, 3)

            # 验证图像格式为 BGR
            assert image.dtype == np.uint8

            # 验证图像内容有效
            mean_value = image.mean()
            assert 0 < mean_value < 255
        except ValueError as e:
            # 如果是魔改版本返回 raw 而不是 JPEG，跳过此测试
            if "Failed to decode JPEG" in str(e):
                pytest.skip(
                    "Minicap appears to be modified to return raw data instead of JPEG. "
                    "This is expected for custom minicap builds."
                )
            raise
    finally:
        mc.close()


@pytest.mark.e2e
def test_minicap_multiple_captures(minicap: MiniCap):
    """测试连续多次截图。"""
    images = []
    for i in range(3):
        img = minicap.screencap()
        images.append(img)

        # 验证每次截图的尺寸一致
        assert img.shape == (minicap.height, minicap.width, 3)

    # 验证所有截图都是有效的
    for i, img in enumerate(images):
        mean_value = img.mean()
        assert 0 < mean_value < 255, (
            f"Image {i} appears to be invalid (mean={mean_value})"
        )


@pytest.mark.e2e
def test_minicap_save_screencap(minicap: MiniCap, tmp_path):
    """测试保存截图功能。"""
    # 保存截图到临时目录
    output_file = tmp_path / "test_minicap_screenshot.png"
    minicap.save_screencap(str(output_file))

    # 验证文件已创建
    assert output_file.exists()

    # 验证可以读取保存的图像
    saved_image = cv2.imread(str(output_file))
    assert saved_image is not None
    assert saved_image.shape == (minicap.height, minicap.width, 3)


@pytest.mark.e2e
def test_minicap_context_manager(device_serial: str, check_minicap_support):
    """测试上下文管理器功能。"""
    with MiniCap(serial=device_serial) as mc:
        image = mc.screencap()
        assert isinstance(image, np.ndarray)
        assert image.shape == (mc.height, mc.width, 3)


@pytest.mark.e2e
def test_minicap_quality_parameter(device_serial: str, check_minicap_support):
    """测试不同质量参数。"""
    mc = MiniCap(serial=device_serial, quality=80, use_stream=True)
    try:
        assert mc.quality == 80
        image = mc.screencap()
        assert isinstance(image, np.ndarray)
    finally:
        mc.close()


@pytest.mark.e2e
def test_minicap_skip_frame_parameter(device_serial: str, check_minicap_support):
    """测试跳帧参数。"""
    mc = MiniCap(serial=device_serial, skip_frame=True, use_stream=True)
    try:
        assert mc.skip_frame is True
        image = mc.screencap()
        assert isinstance(image, np.ndarray)
    finally:
        mc.close()


@pytest.mark.e2e
def test_minicap_performance(minicap: MiniCap):
    """测试截图性能（确保在合理时间内完成）。"""
    import time

    # 预热
    minicap.screencap()

    # 测试性能
    start = time.time()
    for _ in range(5):
        minicap.screencap()
    elapsed = time.time() - start

    avg_time = elapsed / 5
    print(f"\nAverage Minicap screencap time: {avg_time*1000:.2f}ms")

    # Minicap stream 模式通常很快，确保单次截图在 2 秒内完成
    assert avg_time < 2.0, (
        f"Minicap screencap is too slow: {avg_time:.2f}s per capture"
    )


@pytest.mark.e2e
def test_minicap_device_info(minicap: MiniCap):
    """测试设备信息获取。"""
    assert minicap.abi is not None
    assert minicap.sdk is not None
    assert minicap.vm_size is not None
    assert minicap.rotation is not None
    assert minicap.rate is not None

    # 验证分辨率格式
    assert "x" in minicap.vm_size
    width_str, height_str = minicap.vm_size.split("x")
    assert int(width_str) > 0
    assert int(height_str) > 0

    # 验证旋转角度
    assert minicap.rotation in [0, 90, 180, 270]
