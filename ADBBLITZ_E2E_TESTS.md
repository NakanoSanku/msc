# ADBBlitz E2E 测试文档

本文档说明为 ADBBlitz 添加的各种 E2E 实测。

## 测试文件概览

### 1. test.py - 基础功能测试
**位置**: `/home/insider/msc/test.py`

**用途**: 快速验证所有截图后端的基本功能

**测试内容**:
- 测试 ADBCap 截图并保存到 `adb.png`
- **测试 ADBBlitz 截图并保存到 `adbblitz.png`** ✨ (新增)
- 测试 MiniCap 截图并保存到 `minicap.png`
- 测试 DroidCast 截图并保存到 `droidcast.png`

**运行方式**:
```bash
# 确保有 Android 设备连接
python test.py
```

**预期结果**:
- 生成 4 个截图文件 (包括 `adbblitz.png`)
- 所有截图应该是当前设备屏幕内容

---

### 2. test_adbblitz.py - ADBBlitz 专项测试
**位置**: `/home/insider/msc/test_adbblitz.py`

**用途**: 全面测试 ADBBlitz 的各项功能和性能

**测试内容**:

#### 测试 1: 基本截图功能
- 初始化 ADBBlitz
- 获取设备分辨率
- 截图并保存
- 测量截图延迟

#### 测试 2: 连续截图性能测试
- 预热 3 次
- 连续截图 10 次
- 统计平均延迟、最小/最大延迟、FPS
- 验证性能是否达标 (< 100ms)

#### 测试 3: 流式迭代器测试
- 使用 `for frame in ab` 迭代器
- 捕获 5 帧
- 计算实际 FPS
- 验证迭代器是否正常工作

#### 测试 4: 原始字节数据测试
- 调用 `screencap_raw()`
- 验证返回的 RGBA 字节数据大小
- 确保数据格式正确

**运行方式**:
```bash
python test_adbblitz.py
```

**预期输出**:
```
使用设备: 127.0.0.1:5555

============================================================
测试 1: 基本截图功能
============================================================
设备分辨率: 1920x1080
正在截图...
✓ 截图成功 (耗时: 45.23ms)
  保存到: adbblitz.png

============================================================
测试 2: 连续截图性能测试
============================================================
预热中...
测试 10 次连续截图...
  第 1 次: 42.15ms
  第 2 次: 38.92ms
  ...

性能统计:
  平均延迟: 41.23ms
  最小延迟: 35.67ms
  最大延迟: 48.91ms
  FPS: 24.25

✓ 性能测试通过 (平均延迟 < 100ms)

============================================================
测试 3: 流式迭代器测试
============================================================
捕获 5 帧...
  捕获第 1 帧: (1080, 1920, 3)
  ...

流式测试结果:
  捕获帧数: 5
  总耗时: 0.21s
  实际 FPS: 23.81

✓ 流式迭代测试通过

============================================================
测试 4: 原始字节数据测试
============================================================
原始数据大小: 8294400 bytes
期望大小: 8294400 bytes
✓ 原始数据测试通过

============================================================
✓ 所有测试通过!
============================================================

ADBBlitz 工作正常，可以使用。
```

---

### 3. performance_test.py - 性能基准测试
**位置**: `/home/insider/msc/performance_test.py`

**用途**: 对比所有截图方案的性能，生成详细报告

**新增内容**:
- 添加 `test_adbblitz()` 方法 ✨
- 在 `run_all_tests()` 中集成 ADBBlitz 测试

**测试指标**:
- 平均延迟 (ms)
- 最小/最大延迟 (ms)
- 中位数延迟 (ms)
- P95/P99 延迟 (ms)
- 标准差 (稳定性)
- FPS (帧率)
- 初始化时间
- 首帧延迟
- 成功率
- 图像分辨率和大小

**运行方式**:
```bash
# 默认配置 (50 次迭代, 3 次预热)
python performance_test.py

# 自定义配置
python performance_test.py --iterations 100 --warmup 5

# 指定设备
python performance_test.py --serial 127.0.0.1:5555

# 自定义输出目录
python performance_test.py --output my_results
```

**生成报告**:
- `performance_results/performance_report.json` - JSON 格式的详细数据
- `performance_results/performance_report.md` - Markdown 格式的可读报告
- `performance_results/latency_distribution.json` - 延迟分布数据

**报告示例** (performance_report.md):
```markdown
# MSC 框架性能测试报告

**测试时间**: 2025-12-13 15:30:00

## 性能摘要

| 方案 | 平均延迟 | 中位延迟 | P95延迟 | FPS | 初始化时间 | 首帧延迟 | 成功率 |
|------|----------|----------|---------|-----|------------|----------|--------|
| ADBCap | 487.23ms | 485.12ms | 512.45ms | 2.05 | 123.45ms | 489.23ms | 100.0% |
| ADBBlitz | 41.23ms | 39.87ms | 48.91ms | 24.25 | 1234.56ms | 987.65ms | 100.0% |
| DroidCast | 89.34ms | 87.23ms | 98.76ms | 11.19 | 2345.67ms | 156.78ms | 100.0% |
| MiniCap | 38.45ms | 37.21ms | 45.32ms | 26.01 | 3456.78ms | 234.56ms | 100.0% |

## 性能对比分析

**延迟最低**: MiniCap (38.45ms)

**FPS最高**: MiniCap (26.01 fps)

**最稳定**: ADBBlitz (标准差 3.21ms)

**初始化最快**: ADBCap (123.45ms)
```

---

## 测试场景对比

| 测试文件 | 用途 | 测试深度 | 运行时间 | 适用场景 |
|---------|------|---------|---------|---------|
| test.py | 快速验证 | 基础 | ~10秒 | 开发时快速检查 |
| test_adbblitz.py | 专项测试 | 全面 | ~30秒 | 验证 ADBBlitz 各项功能 |
| performance_test.py | 性能基准 | 深入 | ~5分钟 | 性能对比和优化决策 |

---

## 测试前提条件

1. **已连接 Android 设备或模拟器**
   ```bash
   adb devices
   ```

2. **已安装依赖**
   ```bash
   uv sync
   ```

3. **设备支持 screenrecord** (Android 4.4+)
   ```bash
   adb shell screenrecord --help
   ```

---

## 故障排查

### 问题 1: 没有设备连接
**错误**: `错误: 没有连接的 Android 设备`

**解决**:
```bash
# 检查设备连接
adb devices

# USB 连接
adb connect 127.0.0.1:5555

# 重启 ADB
adb kill-server
adb start-server
```

### 问题 2: ADBBlitz 初始化失败
**错误**: `Failed to initialize ADBBlitz`

**可能原因**:
- 设备不支持 H264 输出格式
- 自定义分辨率不支持
- ADB 连接不稳定

**解决**:
```python
# 使用默认分辨率
ab = ADBBlitz(serial=serial)  # 不指定 width/height

# 如果仍然失败，使用 ADBCap 作为后备
from msc.adbcap import ADBCap
ab = ADBCap(serial=serial)
```

### 问题 3: 性能测试太慢
**建议**: 减少测试迭代次数
```bash
python performance_test.py --iterations 10 --warmup 1
```

---

## 性能预期

基于 adbnativeblitz 库，ADBBlitz 的性能预期:

- **平均延迟**: 30-60ms (取决于设备和分辨率)
- **FPS**: 15-30 (连续捕获)
- **初始化时间**: 1-3秒 (需要启动 H264 流)
- **首帧延迟**: 500-1500ms (等待第一帧解码)
- **稳定性**: 很高 (标准差 < 5ms)

**对比其他方案**:
- 比 ADBCap 快 ~10倍
- 与 MiniCap 性能相当
- 比 DroidCast 快 ~2倍
- 无需安装额外组件 (相比 MiniCap/DroidCast)

---

## 总结

通过以上三个测试文件，我们可以:

1. ✅ **快速验证** - `test.py` 确保基本功能正常
2. ✅ **全面测试** - `test_adbblitz.py` 验证所有功能特性
3. ✅ **性能对比** - `performance_test.py` 生成详细的性能报告

这些测试覆盖了 ADBBlitz 的所有关键功能:
- 基本截图 (`screencap()`)
- 原始字节 (`screencap_raw()`)
- 保存文件 (`save_screencap()`)
- 流式迭代 (`for frame in ab`)
- 上下文管理器 (`with ADBBlitz()`)
- 性能指标 (延迟、FPS、稳定性)
