# DroidCast 测试

本目录包含 DroidCast 截图功能的单元测试和端到端测试。

## 测试类型

### 单元测试 (Unit Tests)
位于 `test_droidcast.py`，使用 mock 进行测试，不需要真实设备。

- 测试 RGBA 到 BGR 的颜色转换
- 测试重试和错误处理机制

###端到端测试 (E2E Tests)
位于 `test_droidcast_e2e.py`，需要真实的 Android 设备或模拟器连接。

**注意事项**：
- DroidCast 使用端口转发机制，可能会出现端口冲突
- 建议在运行 e2e 测试前清理所有端口转发：
  ```python
  from adbutils import adb
  d = adb.device_list()[0]
  for f in d.forward_list():
      d.forward_remove(f)
  ```
- 使用 module scope fixture 以避免频繁创建销毁实例

## 运行测试

### 运行所有测试
```bash
uv run pytest -v msc-droidcast/tests/
```

### 仅运行单元测试
```bash
uv run pytest -v -m unit msc-droidcast/tests/
```

### 仅运行 e2e 测试
```bash
uv run pytest -v -m e2e msc-droidcast/tests/
```

## 环境要求

### 单元测试
- Python >= 3.9
- pytest
- adbutils
- opencv-python-headless
- numpy
- requests

### E2E 测试
除了单元测试的要求外，还需要：
- 连接的 Android 设备或模拟器
- DroidCast APK 会自动安装到设备

## 测试覆盖率

当前测试覆盖：
- ✅ RGBA 到 BGR 颜色转换
- ✅ 连接错误重试机制
- ✅ DroidCast APK 安装和版本管理
- ✅ 端口转发
- ✅ 截图获取
- ✅ 多次截图
- ✅ 保存截图
- ✅ Display ID 支持
- ✅ 自定义端口
- ✅ 进程重启
- ✅ 性能测试
