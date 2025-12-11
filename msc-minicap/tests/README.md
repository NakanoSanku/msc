# Minicap 测试

本目录包含 Minicap 截图功能的单元测试和端到端测试。

## 测试类型

### 单元测试 (Unit Tests)
位于 `test_minicap.py`，使用 mock 进行测试，不需要真实设备。

- 测试 MiniCapStream 读取单帧数据
- 测试 RGBA 到 BGR 的颜色转换

### 端到端测试 (E2E Tests)
位于 `test_minicap_e2e.py`，需要真实的 Android 设备或模拟器连接。

**注意事项**：
- **Minicap 仅支持 Android SDK <= 34**
- Minicap 使用端口转发机制，可能会出现端口冲突
- 建议在运行 e2e 测试前清理所有端口转发
- 使用 module scope fixture 以避免频繁创建销毁实例
- 支持 stream 和 非-stream 两种模式

## 运行测试

### 运行所有测试
```bash
uv run pytest -v msc-minicap/tests/
```

### 仅运行单元测试
```bash
uv run pytest -v -m unit msc-minicap/tests/
```

### 仅运行 e2e 测试
```bash
uv run pytest -v -m e2e msc-minicap/tests/
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
- 连接的 Android 设备或模拟器（SDK <= 34）
- Minicap 二进制文件会自动推送到设备

## SDK 版本限制

Minicap 最高支持 Android SDK 34。如果设备 SDK > 34，e2e 测试会自动跳过并显示警告：
```
SKIPPED: Minicap does not support Android SDK 35 (Max 34)
```

## 自定义 Minicap 构建

**注意**：如果你使用的是魔改版本的 Minicap（例如直接返回 raw 数据而不是 JPEG），非-stream 模式的测试可能会跳过：

```
SKIPPED: Minicap appears to be modified to return raw data instead of JPEG.
This is expected for custom minicap builds.
```

这是预期行为，不会影响其他测试。

## 测试覆盖率

当前测试覆盖：
- ✅ MiniCapStream 协议解析
- ✅ RGBA 到 BGR 颜色转换
- ✅ SDK 版本检查
- ✅ Minicap 安装和推送
- ✅ Stream 模式截图
- ✅ 非-Stream 模式截图（JPEG）
- ✅ 多次连续截图
- ✅ 保存截图
- ✅ Quality 参数
- ✅ Skip frame 参数
- ✅ 设备信息获取
- ✅ 性能测试
