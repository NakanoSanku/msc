# MSC 截图功能测试套件

本项目包含多个Android 屏幕截图后端的完整测试套件，包括单元测试和端到端测试。

## 支持的截图后端

1. **ADB (msc-adb)** - 使用 `adb exec-out screencap` 命令
2. **DroidCast (msc-droidcast)** - 基于 HTTP 的截图服务
3. **Minicap (msc-minicap)** - 高性能截图流（SDK <= 34）
4. **MuMu (msc-mumu)** - MuMu 模拟器专用（仅 Windows）

## 测试架构

### 测试标记 (Markers)

使用 pytest markers 区分不同类型的测试：

- `@pytest.mark.unit` - 单元测试，使用 mock/monkeypatch，不需要真实设备
- `@pytest.mark.e2e` - 端到端测试，需要真实的 Android 设备或模拟器

### 测试组织

```
msc/
├── pytest.ini                    # Pytest 配置
├── msc-adb/tests/
│   ├── test_adbcap.py           # 单元测试
│   ├── test_adbcap_e2e.py       # E2E 测试
│   └── README.md
├── msc-droidcast/tests/
│   ├── test_droidcast.py        # 单元测试
│   ├── test_droidcast_e2e.py    # E2E 测试
│   └── README.md
├── msc-minicap/tests/
│   ├── test_minicap.py          # 单元测试
│   ├── test_minicap_e2e.py      # E2E 测试
│   └── README.md
└── msc-mumu/tests/
    ├── test_mumu.py             # 单元测试
    ├── test_mumu_e2e.py         # E2E 测试（仅 Windows）
    └── README.md
```

## 快速开始

### 安装依赖

```bash
uv sync
```

### 运行所有测试

```bash
# 运行所有测试（单元测试 + E2E 测试）
uv run pytest -v

# 仅运行单元测试（不需要设备）
uv run pytest -v -m unit

# 仅运行 E2E 测试（需要设备）
uv run pytest -v -m e2e

# 跳过 E2E 测试
uv run pytest -v -m "not e2e"
```

### 运行特定模块的测试

```bash
# ADB 测试
uv run pytest -v msc-adb/tests/

# DroidCast 测试
uv run pytest -v msc-droidcast/tests/

# Minicap 测试
uv run pytest -v msc-minicap/tests/

# MuMu 测试（Windows）
uv run pytest -v msc-mumu/tests/
```

## E2E 测试要求

### 设备连接

E2E 测试需要连接 Android 设备或模拟器：

```bash
# 检查设备连接
python -c "from adbutils import adb; print(adb.device_list())"
```

如果没有设备连接，E2E 测试会自动跳过。

### 清理端口转发

DroidCast 和 Minicap 使用端口转发，可能会出现端口冲突。建议测试前清理：

```python
from adbutils import adb
d = adb.device_list()[0]
for f in d.forward_list():
    d.forward_remove(f)
```

或使用命令行：

```bash
uv run python -c "from adbutils import adb; d = adb.device_list()[0]; [d.forward_remove(f) for f in d.forward_list()]"
```

### SDK 版本要求

- **ADB**: 所有 Android 版本
- **DroidCast**: 所有 Android 版本
- **Minicap**: Android SDK <= 34
- **MuMu**: 仅 Windows 平台 + MuMu 模拟器

## 测试覆盖

### ADB (9个 E2E 测试)

- ✅ ADBCap 初始化
- ✅ 原始截图获取
- ✅ OpenCV 格式截图
- ✅ 连续多次截图
- ✅ 保存截图
- ✅ Display ID 支持
- ✅ 上下文管理器
- ✅ 性能测试
- ✅ 无效设备处理

### DroidCast (11个 E2E 测试)

- ✅ DroidCast 初始化和 APK 安装
- ✅ 原始截图获取
- ✅ OpenCV 格式截图
- ✅ 连续多次截图
- ✅ 保存截图
- ✅ Display ID 支持
- ✅ 上下文管理器
- ✅ 进程重启
- ✅ 性能测试
- ✅ 自定义端口
- ✅ APK 版本检查

### Minicap (12个 E2E 测试)

- ✅ Minicap 初始化和安装
- ✅ SDK 版本检查
- ✅ Stream 模式原始截图
- ✅ Stream 模式 OpenCV 截图
- ✅ 非-Stream 模式截图（JPEG）
- ✅ 连续多次截图
- ✅ 保存截图
- ✅ 上下文管理器
- ✅ Quality 参数
- ✅ Skip frame 参数
- ✅ 性能测试
- ✅ 设备信息获取

### MuMu (12个 E2E 测试，仅 Windows)

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

## 单元测试统计

- **总计**: 11 个单元测试
  - ADB: 5 个
  - DroidCast: 2 个
  - Minicap: 2 个
  - MuMu: 2 个

## E2E 测试统计

- **总计**: 44 个 E2E 测试
  - ADB: 9 个
  - DroidCast: 11 个
  - Minicap: 12 个
  - MuMu: 12 个（仅 Windows）

## 常见问题

### Q: E2E 测试失败并提示 "No Android devices connected"
A: 确保有设备通过 ADB 连接。使用 `adb devices` 或 adbutils 检查设备列表。

### Q: DroidCast/Minicap 测试失败并提示端口绑定错误
A: 清理所有端口转发后重试（见上方"清理端口转发"部分）。

### Q: Minicap 测试跳过并提示 SDK 不支持
A: Minicap 仅支持 Android SDK <= 34。如果您的设备 SDK > 34，这是正常行为。

### Q: MuMu 测试在 Linux/macOS 上跳过
A: MuMu 仅支持 Windows 平台。在非 Windows 平台上，e2e 测试会自动跳过。

### Q: MuMu 测试失败并提示 "MuMu emulator not found"
A: 确保 MuMu 模拟器已正确安装且至少有一个实例正在运行。

### Q: 单元测试运行失败
A: 确保所有依赖已安装：`uv sync`

## 使用 adbutils 包

所有测试都使用 `adbutils` 包提供的 ADB 功能，**不依赖系统环境中的 adb 命令**。这确保了测试的可移植性和一致性。

## 持续集成

在 CI 环境中，建议：

1. 仅运行单元测试（不需要设备）：
   ```bash
   uv run pytest -v -m unit
   ```

2. 如果有模拟器环境，可以运行完整测试：
   ```bash
   # 启动模拟器
   # 运行所有测试
   uv run pytest -v
   ```

## 贡献指南

添加新测试时：

1. 单元测试应标记为 `@pytest.mark.unit`
2. E2E 测试应标记为 `@pytest.mark.e2e`
3. E2E 测试应使用 fixture 来管理设备连接和清理
4. 更新相应的 README.md 文档
