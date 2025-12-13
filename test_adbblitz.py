#!/usr/bin/env python3
"""
ADBBlitz 快速测试脚本

用于快速验证 ADBBlitz 功能是否正常工作。

运行方式:
    python test_adbblitz.py
"""

import time

from adbutils import adb

from msc.adbblitz import ADBBlitz

# 获取第一个设备
devices = adb.device_list()
if not devices:
    print("错误: 没有连接的 Android 设备")
    print("请连接设备后重试")
    exit(1)

serial = devices[0].serial
print(f"使用设备: {serial}")

# 测试 1: 基本截图
print("\n" + "=" * 60)
print("测试 1: 基本截图功能")
print("=" * 60)
try:
    with ADBBlitz(serial=serial) as ab:
        print(f"设备分辨率: {ab.width}x{ab.height}")

        # 截图并保存
        print("正在截图...")
        start = time.time()
        ab.save_screencap("adbblitz.png")
        elapsed = (time.time() - start) * 1000

        print(f"✓ 截图成功 (耗时: {elapsed:.2f}ms)")
        print(f"  保存到: adbblitz.png")
except Exception as e:
    print(f"✗ 截图失败: {e}")
    exit(1)

# 测试 2: 连续截图性能
print("\n" + "=" * 60)
print("测试 2: 连续截图性能测试")
print("=" * 60)
try:
    with ADBBlitz(serial=serial) as ab:
        # 预热
        print("预热中...")
        for _ in range(3):
            ab.screencap()

        # 性能测试
        print("测试 10 次连续截图...")
        latencies = []
        for i in range(10):
            start = time.time()
            img = ab.screencap()
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            print(f"  第 {i+1} 次: {elapsed:.2f}ms")

        # 统计
        import numpy as np
        avg = np.mean(latencies)
        min_lat = np.min(latencies)
        max_lat = np.max(latencies)

        print(f"\n性能统计:")
        print(f"  平均延迟: {avg:.2f}ms")
        print(f"  最小延迟: {min_lat:.2f}ms")
        print(f"  最大延迟: {max_lat:.2f}ms")
        print(f"  FPS: {1000/avg:.2f}")

        if avg < 100:
            print("\n✓ 性能测试通过 (平均延迟 < 100ms)")
        else:
            print(f"\n⚠ 性能较慢 (平均延迟 {avg:.2f}ms)")

except Exception as e:
    print(f"✗ 性能测试失败: {e}")
    exit(1)

# 测试 3: 流式迭代
print("\n" + "=" * 60)
print("测试 3: 流式迭代器测试")
print("=" * 60)
try:
    with ADBBlitz(serial=serial) as ab:
        print("捕获 5 帧...")
        frame_count = 0
        start_time = time.time()

        for frame in ab:
            frame_count += 1
            print(f"  捕获第 {frame_count} 帧: {frame.shape}")

            if frame_count >= 5:
                break

            # 超时保护
            if time.time() - start_time > 10:
                print("  超时，停止测试")
                break

        elapsed = time.time() - start_time
        fps = frame_count / elapsed

        print(f"\n流式测试结果:")
        print(f"  捕获帧数: {frame_count}")
        print(f"  总耗时: {elapsed:.2f}s")
        print(f"  实际 FPS: {fps:.2f}")

        if frame_count >= 5:
            print("\n✓ 流式迭代测试通过")
        else:
            print(f"\n⚠ 只捕获了 {frame_count} 帧")

except Exception as e:
    print(f"✗ 流式测试失败: {e}")
    exit(1)

# 测试 4: 原始字节数据
print("\n" + "=" * 60)
print("测试 4: 原始字节数据测试")
print("=" * 60)
try:
    with ADBBlitz(serial=serial) as ab:
        raw_data = ab.screencap_raw()
        expected_size = ab.width * ab.height * 4  # RGBA

        print(f"原始数据大小: {len(raw_data)} bytes")
        print(f"期望大小: {expected_size} bytes")

        if len(raw_data) == expected_size:
            print("✓ 原始数据测试通过")
        else:
            print(f"✗ 数据大小不匹配")
            exit(1)

except Exception as e:
    print(f"✗ 原始数据测试失败: {e}")
    exit(1)

# 全部测试通过
print("\n" + "=" * 60)
print("✓ 所有测试通过!")
print("=" * 60)
print("\nADBBlitz 工作正常，可以使用。")
