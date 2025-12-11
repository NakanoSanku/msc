# ADB 截图测试

本目录包含 ADB 截图功能的单元测试和端到端测试。

## 测试类型

### 单元测试 (Unit Tests)
位于 `test_adbcap.py`，使用 mock 和 monkeypatch 进行测试，不需要真实设备。

- 测试 `_run_adb_command` 函数的各种场景
- 测试 RGBA 到 BGR 的颜色转换
- 测试错误处理和超时场景

### 端到端测试 (E2E Tests)
位于 `test_adbcap_e2e.py`，需要真实的 Android 设备或模拟器连接。

- 测试 ADBCap 初始化
- 测试原始截图功能
- 测试 OpenCV 格式截图
- 测试连续截图
- 测试保存截图
- 测试指定 display_id
- 测试上下文管理器
- 测试性能
- 测试无效设备处理

## 运行测试

### 运行所有测试
```bash
uv run pytest -v msc-adb/tests/
```

### 仅运行单元测试
```bash
uv run pytest -v -m unit msc-adb/tests/
```

### 仅运行 e2e 测试
```bash
uv run pytest -v -m e2e msc-adb/tests/
```

### 跳过 e2e 测试（仅运行不需要设备的测试）
```bash
uv run pytest -v -m "not e2e" msc-adb/tests/
```

## 环境要求

### 单元测试
- Python >= 3.9
- pytest
- adbutils
- opencv-python-headless
- numpy

### E2E 测试
除了单元测试的要求外，还需要：
- 连接的 Android 设备或模拟器
- adbutils 包（不需要系统环境中的 adb 命令）

## 设备连接

E2E 测试使用 `adbutils` 包提供的 ADB 功能，**不依赖系统环境中的 adb 命令**。

检查设备连接：
```python
from adbutils import adb
devices = adb.device_list()
print(devices)
```

如果没有设备连接，e2e 测试将自动跳过。

## 测试覆盖率

当前测试覆盖：
- ✅ ADB 命令执行和错误处理
- ✅ 截图数据获取和转换
- ✅ 颜色格式转换（RGBA → BGR）
- ✅ 多次连续截图
- ✅ 截图保存功能
- ✅ Display ID 支持
- ✅ 上下文管理器
- ✅ 性能验证
- ✅ 异常场景处理
