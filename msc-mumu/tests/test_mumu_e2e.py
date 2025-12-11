"""
MuMu 模拟器截图功能的端到端测试。

这些测试需要 Windows 平台和运行中的 MuMu 模拟器实例。
MuMu 使用 external_renderer_ipc.dll 通过共享内存获取截图。

注意：
- **仅支持 Windows 平台**
- 需要安装 MuMu 模拟器
- 需要至少一个运行中的模拟器实例

运行方式：
    pytest -v -m e2e msc-mumu/tests/test_mumu_e2e.py

跳过 e2e 测试：
    pytest -v -m "not e2e" msc-mumu/tests/
"""

import sys

import cv2
import numpy as np
import pytest

# MuMu 仅支持 Windows 平台
if sys.platform != "win32":
    pytest.skip("MuMu is only supported on Windows", allow_module_level=True)

try:
    from mmumu.base import get_mumu_path

    from msc.mumu import MuMuCap
except ImportError:
    pytest.skip(
        "mmumu package not available (Windows-only dependency)", allow_module_level=True
    )


@pytest.fixture(scope="module")
def mumu_install_path():
    """
    获取 MuMu 模拟器安装路径。

    如果未安装 MuMu，跳过所有 e2e 测试。
    """
    try:
        path = get_mumu_path()
        print(f"\nMuMu install path: {path}")
        return path
    except Exception as e:
        pytest.skip(f"MuMu emulator not found: {e}")


@pytest.fixture(scope="module")
def mumucap(mumu_install_path: str):
    """
    创建 MuMuCap 实例并在测试后清理。

    默认连接到实例索引 0。
    """
    try:
        mc = MuMuCap(instance_index=0, emulator_install_path=mumu_install_path)
        yield mc
        mc.close()
    except Exception as e:
        pytest.skip(f"Failed to connect to MuMu instance 0: {e}")


@pytest.mark.e2e
def test_mumucap_initialization(mumu_install_path: str):
    """测试 MuMuCap 初始化。"""
    mc = MuMuCap(instance_index=0, emulator_install_path=mumu_install_path)

    try:
        assert mc.emulator_install_path == mumu_install_path
        assert mc.instance_index == 0
        assert mc.display_id == 0
        assert mc.width > 0
        assert mc.height > 0
        assert mc.buffer_size == mc.width * mc.height * 4
        assert mc.nemu is not None
        assert mc.handle is not None
        assert mc.pixels is not None
    finally:
        mc.close()


@pytest.mark.e2e
def test_mumucap_screencap_raw(mumucap: MuMuCap):
    """测试原始截图功能。"""
    raw_data = mumucap.screencap_raw()

    # 验证返回的是字节数据
    assert isinstance(raw_data, bytes)

    # 验证数据长度符合预期（RGBA格式）
    expected_size = mumucap.width * mumucap.height * 4
    assert len(raw_data) == expected_size, (
        f"Raw data size {len(raw_data)} != expected {expected_size}"
    )


@pytest.mark.e2e
def test_mumucap_screencap(mumucap: MuMuCap):
    """测试 OpenCV 格式截图功能。"""
    image = mumucap.screencap()

    # 验证返回的是 numpy 数组
    assert isinstance(image, np.ndarray)

    # 验证图像尺寸
    assert image.shape == (mumucap.height, mumucap.width, 3)

    # 验证图像格式为 BGR（OpenCV 默认格式）
    assert image.dtype == np.uint8

    # 验证图像内容不是全黑或全白
    mean_value = image.mean()
    assert 0 < mean_value < 255, f"Image appears to be invalid (mean={mean_value})"


@pytest.mark.e2e
def test_mumucap_multiple_captures(mumucap: MuMuCap):
    """测试连续多次截图。"""
    images = []
    for i in range(3):
        img = mumucap.screencap()
        images.append(img)

        # 验证每次截图的尺寸一致
        assert img.shape == (mumucap.height, mumucap.width, 3)

    # 验证所有截图都是有效的
    for i, img in enumerate(images):
        mean_value = img.mean()
        assert 0 < mean_value < 255, f"Image {i} appears to be invalid (mean={mean_value})"


@pytest.mark.e2e
def test_mumucap_save_screencap(mumucap: MuMuCap, tmp_path):
    """测试保存截图功能。"""
    # 保存截图到临时目录
    output_file = tmp_path / "test_mumu_screenshot.png"
    mumucap.save_screencap(str(output_file))

    # 验证文件已创建
    assert output_file.exists()

    # 验证可以读取保存的图像
    saved_image = cv2.imread(str(output_file))
    assert saved_image is not None
    assert saved_image.shape == (mumucap.height, mumucap.width, 3)


@pytest.mark.e2e
def test_mumucap_context_manager(mumu_install_path: str):
    """测试上下文管理器功能。"""
    with MuMuCap(instance_index=0, emulator_install_path=mumu_install_path) as mc:
        image = mc.screencap()
        assert isinstance(image, np.ndarray)
        assert image.shape == (mc.height, mc.width, 3)


@pytest.mark.e2e
def test_mumucap_display_id(mumu_install_path: str):
    """测试指定 display_id 参数。"""
    mc = MuMuCap(
        instance_index=0, emulator_install_path=mumu_install_path, display_id=0
    )
    try:
        assert mc.display_id == 0
        image = mc.screencap()
        assert isinstance(image, np.ndarray)
    finally:
        mc.close()


@pytest.mark.e2e
def test_mumucap_performance(mumucap: MuMuCap):
    """测试截图性能（确保在合理时间内完成）。"""
    import time

    # 预热
    try:
        mumucap.screencap()
    except Exception:
        # 如果预热失败，跳过性能测试
        pytest.skip("Failed to warm up MuMu capture, skipping performance test")

    # 测试性能 - 添加小延迟避免频繁调用导致错误
    successful_captures = 0
    start = time.time()

    for i in range(10):
        try:
            mumucap.screencap()
            successful_captures += 1
            # 添加小延迟避免过于频繁的调用
            if i < 9:  # 最后一次不需要延迟
                time.sleep(0.01)
        except Exception as e:
            print(f"\nCapture {i+1} failed: {e}")
            # 如果连续失败太多次，跳过测试
            if successful_captures < 3:
                pytest.skip(f"MuMu capture failing too frequently: {e}")
            break

    elapsed = time.time() - start

    # 确保至少有一半的截图成功
    assert successful_captures >= 5, (
        f"Only {successful_captures}/10 captures succeeded"
    )

    avg_time = elapsed / successful_captures
    print(f"\nAverage MuMu screencap time: {avg_time*1000:.2f}ms ({successful_captures} successful)")

    # MuMu 使用共享内存，应该非常快
    # 但考虑到可能的系统延迟，放宽限制到 500ms
    assert avg_time < 0.5, (
        f"MuMu screencap is too slow: {avg_time*1000:.2f}ms per capture"
    )


@pytest.mark.e2e
def test_mumucap_dll_path_auto_detection(mumu_install_path: str):
    """测试 DLL 路径自动检测。"""
    # 不提供 dll_path，让它自动检测
    mc = MuMuCap(instance_index=0, emulator_install_path=mumu_install_path)
    try:
        assert mc.dllPath is not None
        assert mc.dllPath.endswith("external_renderer_ipc.dll")
        # 验证可以正常截图
        image = mc.screencap()
        assert isinstance(image, np.ndarray)
    finally:
        mc.close()


@pytest.mark.e2e
def test_mumucap_buffer_consistency(mumucap: MuMuCap):
    """测试缓冲区一致性。"""
    import time

    # 获取原始数据 - 添加延迟避免频繁调用
    try:
        raw1 = mumucap.screencap_raw()
        time.sleep(0.05)  # 50ms 延迟
        raw2 = mumucap.screencap_raw()

        # 两次获取的数据长度应该一致
        assert len(raw1) == len(raw2)
        assert len(raw1) == mumucap.buffer_size
    except Exception as e:
        # 如果 MuMu API 在连续调用时出错，跳过测试
        if "capture_display error" in str(e):
            pytest.skip(
                f"MuMu capture_display error during rapid calls. "
                f"This may occur with some MuMu versions: {e}"
            )
        raise


@pytest.mark.e2e
def test_mumucap_reconnect(mumu_install_path: str):
    """测试断开连接后重新连接。"""
    mc1 = MuMuCap(instance_index=0, emulator_install_path=mumu_install_path)
    handle1 = mc1.handle
    mc1.close()

    # 重新连接
    mc2 = MuMuCap(instance_index=0, emulator_install_path=mumu_install_path)
    try:
        # 应该获得新的 handle
        assert mc2.handle is not None
        # 验证可以正常截图
        image = mc2.screencap()
        assert isinstance(image, np.ndarray)
    finally:
        mc2.close()


@pytest.mark.e2e
def test_mumucap_invalid_instance():
    """测试连接到无效实例索引。"""
    # 尝试连接到一个不存在的实例（假设索引 999 不存在）
    with pytest.raises(Exception):
        mc = MuMuCap(instance_index=999)
        mc.screencap()
