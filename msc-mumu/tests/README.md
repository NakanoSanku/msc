# MuMu 模拟器测试

本目录包含 MuMu 模拟器截图功能的单元测试和端到端测试。

## 测试类型

### 单元测试 (Unit Tests)
位于 `test_mumu.py`，使用 mock 进行测试，不需要真实的 MuMu 模拟器。

- 测试 RGBA 到 BGR 的颜色转换
- 测试垂直翻转
- 测试断开连接功能

### 端到端测试 (E2E Tests)
位于 `test_mumu_e2e.py`，需要 Windows 平台和运行中的 MuMu 模拟器实例。

**平台要求**：
- **仅支持 Windows 平台**
- 需要安装 MuMu 模拟器
- 需要至少一个运行中的模拟器实例（默认实例索引 0）

**注意事项**：
- MuMu 使用 `external_renderer_ipc.dll` 通过共享内存获取截图
- 在 Linux/macOS 上，e2e 测试会自动跳过
- 性能非常高（通常 < 10ms per capture）

## 运行测试

### 运行所有测试（Windows）
```bash
uv run pytest -v msc-mumu/tests/
```

### 仅运行单元测试
```bash
uv run pytest -v -m unit msc-mumu/tests/
```

### 仅运行 e2e 测试（Windows + MuMu）
```bash
uv run pytest -v -m e2e msc-mumu/tests/
```

### 在非 Windows 平台
```bash
# 单元测试可以运行（使用 mock）
uv run pytest -v -m unit msc-mumu/tests/

# E2E 测试会自动跳过
uv run pytest -v -m e2e msc-mumu/tests/
# SKIPPED: MuMu is only supported on Windows
```

## 环境要求

### 单元测试
- Python >= 3.9
- pytest
- opencv-python-headless
- numpy

**不需要** Windows 平台或 mmumu 包（使用 mock）

### E2E 测试
除了单元测试的要求外，还需要：
- **Windows 操作系统**
- 安装的 MuMu 模拟器
- mmumu 包（从 GitHub 安装）
- 至少一个运行中的模拟器实例

## MuMu 模拟器检测

E2E 测试会自动检测 MuMu 安装路径（通过注册表）：

```python
from mmumu.base import get_mumu_path
path = get_mumu_path()
```

如果未检测到 MuMu 安装，测试会自动跳过。

## 测试覆盖

### E2E 测试 (12个测试)

- ✅ MuMuCap 初始化
- ✅ 原始截图获取
- ✅ OpenCV 格式截图
- ✅ 连续多次截图
- ✅ 保存截图
- ✅ 上下文管理器
- ✅ Display ID 支持
- ✅ 性能测试
- ✅ DLL 路径自动检测
- ✅ 缓冲区一致性
- ✅ 重新连接
- ✅ 无效实例处理

### 单元测试 (2个测试)

- ✅ RGBA 到 BGR 转换（含垂直翻转）
- ✅ 断开连接功能

## 技术细节

### MuMu 截图原理

MuMu 使用 `external_renderer_ipc.dll` 提供的 API：

1. **连接**: `connect(install_path, instance_index)` → 返回 handle
2. **获取尺寸**: `capture_display(handle, display_id, 0, &width, &height, NULL)`
3. **截图**: `capture_display(handle, display_id, buffer_size, width, height, pixels)`
4. **断开**: `disconnect(handle)`

### 图像格式

- **原始格式**: RGBA（上下颠倒）
- **处理步骤**:
  1. 垂直翻转（`[::-1, :, :]`）
  2. RGBA → BGR 转换（`cv2.cvtColor`）
- **输出格式**: BGR（OpenCV 标准）

### DLL 路径

MuMu 12.0+:
```
<install_path>/shell/sdk/external_renderer_ipc.dll
```

MuMu 12.5+:
```
<install_path>/nx_device/12.0/shell/sdk/external_renderer_ipc.dll
```

代码会自动检测并选择正确的路径。

## 常见问题

### Q: 测试在 Linux/macOS 上失败
A: MuMu 仅支持 Windows。在非 Windows 平台上，e2e 测试会自动跳过。单元测试可以正常运行。

### Q: 提示 "MuMu emulator not found"
A: 确保 MuMu 模拟器已正确安装。检查注册表或手动指定安装路径。

### Q: 提示 "Failed to connect to MuMu instance 0"
A: 确保至少有一个 MuMu 模拟器实例正在运行。

### Q: 提示 "external_renderer_ipc.dll not found"
A: MuMu 版本可能不支持该 DLL。确保使用 MuMu 12.0+ 版本。

### Q: 性能测试或缓冲区测试出现 "capture_display error"
A: MuMu API 在某些版本中可能不支持频繁的连续调用。测试已添加延迟和错误处理：
- 性能测试：每次截图间隔 10ms
- 缓冲区测试：两次截图间隔 50ms
- 如果仍然失败，测试会自动跳过并显示警告

### Q: 单元测试可以运行，但 e2e 测试失败
A: 检查：
1. 是否在 Windows 平台
2. MuMu 是否已安装
3. 模拟器实例是否正在运行
4. mmumu 包是否已安装

## 性能基准

MuMu 截图性能（Windows 平台，实际测试）：

- **平均截图时间**: 5-10 ms
- **分辨率**: 1280x720
- **方法**: 共享内存（零拷贝）

这使得 MuMu 成为所有截图后端中最快的选择。

## 依赖项

MuMu 相关依赖：

```toml
[project]
dependencies = [
    "mmumu",                          # MuMu API 包装（仅 Windows）
    "msc-base",
    "opencv-python-headless>=4.11.0.86",
]

[tool.uv.sources]
mmumu = { git = "https://github.com/NakanoSanku/mmumu" }
```

## CI/CD 注意事项

在持续集成环境中：

1. **Linux/macOS CI**:
   - 仅运行单元测试: `pytest -v -m unit msc-mumu/tests/`
   - E2E 测试会自动跳过

2. **Windows CI**:
   - 如果没有 MuMu 环境，使用: `pytest -v -m unit msc-mumu/tests/`
   - 如果有 MuMu 环境，可运行完整测试

3. **推荐配置**:
   ```yaml
   # .github/workflows/test.yml
   - name: Run MuMu tests
     run: |
       if [ "$RUNNER_OS" == "Windows" ]; then
         uv run pytest -v msc-mumu/tests/
       else
         uv run pytest -v -m unit msc-mumu/tests/
       fi
   ```
