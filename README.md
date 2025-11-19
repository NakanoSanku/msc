# MSC (Multi-Screencap Control) 框架

[![PyPI](https://img.shields.io/pypi/v/msc-base)](https://pypi.org/project/msc-base/)
[![License](https://img.shields.io/github/license/NakanoSanku/msc)](LICENSE)

MSC 是一个统一的 Android 屏幕截图控制框架，旨在为自动化测试、脚本编写和群控系统提供高性能、低延迟的截图解决方案。它通过统一的 `ScreenCap` 接口，屏蔽了底层不同截图方案（ADB, DroidCast, minicap, MuMu）的差异。

## 🌟 特性

- **统一接口**: 所有实现均继承自 `ScreenCap` 抽象基类，支持 Context Manager (`with` 语句)。
- **多方案支持**:
  - **ADB**: 原生兼容性最好，无需额外依赖。
  - **DroidCast**: 基于 HTTP 的截图方案，速度优于 ADB。
  - **minicap**: 经典的低延迟流式截图方案（支持至 Android 14/SDK 34）。
  - **MuMu**: 针对 MuMu 模拟器的深度优化，基于共享内存，**极低延迟 (1-2ms)**。
- **资源管理**: 完善的资源释放机制，防止子进程残留。
- **类型安全**: 提供完整的类型提示 (Type Hints)。

## 📦 安装

推荐使用 `uv` 或 `pip` 进行安装。

### 全量安装
安装包含所有实现方案的版本：

```bash
# 使用 uv (推荐)
uv add "git+https://github.com/NakanoSanku/msc"

# 使用 pip
pip install "git+https://github.com/NakanoSanku/msc"
```

### 按需安装
如果只需要特定的截图方案，可以单独安装对应的子包：

```bash
# 仅安装 minicap 支持
uv add "git+https://github.com/NakanoSanku/msc#subdirectory=msc-minicap"

# 仅安装 MuMu 支持
uv add "git+https://github.com/NakanoSanku/msc#subdirectory=msc-mumu"
```

## 🚀 快速开始

### 基础用法

所有截图控制器都实现了 `screencap()` (返回 OpenCV 图像) 和 `screencap_raw()` (返回原始字节数据)。

```python
import cv2
from msc.adbcap import ADBCap
from msc.droidcast import DroidCast
from msc.minicap import MiniCap
from msc.mumu import MuMuCap

def capture(controller):
    # 使用 with 语句自动管理资源（推荐）
    with controller as cap:
        # 获取 OpenCV 格式图像 (BGR)
        image = cap.screencap()
        print(f"截图尺寸: {image.shape}")
        
        # 保存截图
        cap.save_screencap("screenshot.png")
        
        # 获取原始数据 (通常为 RGBA 字节流)
        raw_data = cap.screencap_raw()
        print(f"原始数据长度: {len(raw_data)}")

# 1. 使用 ADB (通用，无需 Root)
capture(ADBCap("emulator-5554"))

# 2. 使用 DroidCast (通用，HTTP 传输)
capture(DroidCast("emulator-5554"))

# 3. 使用 minicap (低延迟，Android < 15)
# capture(MiniCap("emulator-5554"))

# 4. 使用 MuMu 模拟器 (极速，共享内存)
# 需要指定模拟器实例索引，0通常为第一个实例
capture(MuMuCap(0))
```

## 📊 方案对比

| 特性 | ADB | DroidCast | minicap | MuMu |
| :--- | :--- | :--- | :--- | :--- |
| **原理** | `adb exec-out screencap` | 手机端 HTTP Server | Socket 流式传输 | 模拟器共享内存 |
| **延迟 (1080P)** | 高 (~160ms) | 中 (~40ms) | 低 (~10ms) | **极低 (~2ms)** |
| **Root 权限** | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| **兼容性** | ✅ 全机型 | ✅ 全机型 | ⚠️ Android < 15 (SDK <= 34) | ⚠️ 仅 MuMu 模拟器 |
| **适用场景** | 兼容性测试、低频截图 | 一般自动化脚本 | 高频实时流 (旧机型) | 模拟器高性能挂机 |

## 🛠️ 模块说明

- **`msc-base`**: 定义核心接口 `ScreenCap`。
- **`msc-adb`**: 基于 `adbutils` 的标准实现。
- **`msc-droidcast`**: 集成 [DroidCast](https://github.com/rayworks/DroidCast) APK，通过 HTTP 获取截图。
- **`msc-minicap`**: 集成 [minicap](https://github.com/openstf/minicap) 二进制文件，通过 Socket 获取高帧率数据。
- **`msc-mumu`**: 调用 MuMu 模拟器 `external_renderer_ipc.dll` 接口，直接读取显存数据。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源。
