"""
DroidCast 截图功能的端到端测试。

这些测试需要真实的 Android 设备或模拟器连接。
测试使用 adbutils 包提供的 ADB 功能，不依赖系统环境中的 adb 命令。

运行方式：
    pytest -v -m e2e msc-droidcast/tests/test_droidcast_e2e.py

跳过 e2e 测试：
    pytest -v -m "not e2e" msc-droidcast/tests/
"""

import cv2
import numpy as np
import pytest
from adbutils import adb

from msc.droidcast import DroidCast


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
def droidcast(device_serial: str):
    """
    创建 DroidCast 实例并在测试后清理。
    使用 module scope 以避免频繁创建销毁导致的端口冲突。
    """
    dc = DroidCast(serial=device_serial, timeout=5)
    yield dc
    dc.close()


@pytest.mark.e2e
def test_droidcast_initialization(device_serial: str):
    """测试 DroidCast 初始化和 APK 安装。"""
    dc = DroidCast(serial=device_serial)

    try:
        assert dc.adb is not None
        assert dc.adb.serial == device_serial
        assert dc.width > 0
        assert dc.height > 0
        assert dc.buffer_size == dc.width * dc.height * 4
        assert dc.popen is not None
        assert dc.local_port is not None
        assert dc.url is not None

        # 验证 APK 已安装
        packages = dc.adb.list_packages()
        assert DroidCast.APK_PACKAGE_NAME in packages
    finally:
        dc.close()


@pytest.mark.e2e
def test_droidcast_screencap_raw(droidcast: DroidCast):
    """测试原始截图功能。"""
    raw_data = droidcast.screencap_raw()

    # 验证返回的是字节数据
    assert isinstance(raw_data, bytes)

    # 验证数据长度符合预期（RGBA格式）
    expected_size = droidcast.width * droidcast.height * 4
    assert len(raw_data) >= expected_size, (
        f"Raw data size {len(raw_data)} is less than expected {expected_size}"
    )


@pytest.mark.e2e
def test_droidcast_screencap(droidcast: DroidCast):
    """测试 OpenCV 格式截图功能。"""
    image = droidcast.screencap()

    # 验证返回的是 numpy 数组
    assert isinstance(image, np.ndarray)

    # 验证图像尺寸
    assert image.shape == (droidcast.height, droidcast.width, 3)

    # 验证图像格式为 BGR（OpenCV 默认格式）
    assert image.dtype == np.uint8

    # 验证图像内容不是全黑或全白
    mean_value = image.mean()
    assert 0 < mean_value < 255, (
        f"Image appears to be invalid (mean={mean_value})"
    )


@pytest.mark.e2e
def test_droidcast_multiple_captures(droidcast: DroidCast):
    """测试连续多次截图。"""
    images = []
    for i in range(3):
        img = droidcast.screencap()
        images.append(img)

        # 验证每次截图的尺寸一致
        assert img.shape == (droidcast.height, droidcast.width, 3)

    # 验证所有截图都是有效的
    for i, img in enumerate(images):
        mean_value = img.mean()
        assert 0 < mean_value < 255, (
            f"Image {i} appears to be invalid (mean={mean_value})"
        )


@pytest.mark.e2e
def test_droidcast_save_screencap(droidcast: DroidCast, tmp_path):
    """测试保存截图功能。"""
    # 保存截图到临时目录
    output_file = tmp_path / "test_droidcast_screenshot.png"
    droidcast.save_screencap(str(output_file))

    # 验证文件已创建
    assert output_file.exists()

    # 验证可以读取保存的图像
    saved_image = cv2.imread(str(output_file))
    assert saved_image is not None
    assert saved_image.shape == (droidcast.height, droidcast.width, 3)


@pytest.mark.e2e
def test_droidcast_with_display_id(device_serial: str):
    """测试指定显示器 ID 的截图功能。"""
    dc = DroidCast(serial=device_serial, display_id=0)
    try:
        image = dc.screencap()

        assert isinstance(image, np.ndarray)
        assert image.shape == (dc.height, dc.width, 3)
    finally:
        dc.close()


@pytest.mark.e2e
def test_droidcast_context_manager(device_serial: str):
    """测试上下文管理器功能。"""
    with DroidCast(serial=device_serial) as dc:
        image = dc.screencap()
        assert isinstance(image, np.ndarray)
        assert image.shape == (dc.height, dc.width, 3)


@pytest.mark.e2e
def test_droidcast_restart(droidcast: DroidCast):
    """测试重启 DroidCast 进程。"""
    # 获取初始进程 ID
    assert droidcast.popen is not None
    initial_pid = droidcast.popen.pid

    # 重启
    droidcast.restart()

    # 验证进程已重启
    assert droidcast.popen is not None
    new_pid = droidcast.popen.pid
    assert new_pid != initial_pid

    # 验证重启后仍可截图
    image = droidcast.screencap()
    assert isinstance(image, np.ndarray)
    assert image.shape == (droidcast.height, droidcast.width, 3)


@pytest.mark.e2e
def test_droidcast_performance(droidcast: DroidCast):
    """测试截图性能（确保在合理时间内完成）。"""
    import time

    # 预热
    droidcast.screencap()

    # 测试性能
    start = time.time()
    for _ in range(5):
        droidcast.screencap()
    elapsed = time.time() - start

    avg_time = elapsed / 5
    print(f"\nAverage DroidCast screencap time: {avg_time*1000:.2f}ms")

    # 确保单次截图在 5 秒内完成
    assert avg_time < 5.0, (
        f"DroidCast screencap is too slow: {avg_time:.2f}s per capture"
    )


@pytest.mark.e2e
def test_droidcast_custom_port(device_serial: str):
    """测试使用自定义端口。"""
    dc = DroidCast(serial=device_serial, port=53517)
    try:
        assert dc.remote_port == 53517
        image = dc.screencap()
        assert isinstance(image, np.ndarray)
    finally:
        dc.close()


@pytest.mark.e2e
def test_droidcast_apk_version_check(device_serial: str):
    """测试 APK 版本检查和升级功能。"""
    dc = DroidCast(serial=device_serial)
    try:
        # 验证安装的版本与期望版本一致
        version_name = dc.adb.package_info(DroidCast.APK_PACKAGE_NAME)["version_name"]
        assert version_name == DroidCast.APK_VERSION
    finally:
        dc.close()
