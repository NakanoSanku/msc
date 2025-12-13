# msc-adbblitz

High-performance ADB screenshot backend using H264 streaming.

## Overview

`msc-adbblitz` provides ultra-fast screenshot capture for Android devices by leveraging ADB's `screenrecord` command with H264 video streaming. Unlike traditional ADB screencap methods that capture single PNG images, ADBBlitz maintains a continuous H264 video stream, allowing for low-latency frame capture.

Based on the [adbnativeblitz](https://github.com/hansalemaos/adbnativeblitz) library, this implementation integrates seamlessly with the `msc` screenshot backend architecture.

## Quick Start

```python
from msc.adbblitz import ADBBlitz
from adbutils import adb

# Get first connected device
serial = adb.device_list()[0].serial

# Capture and save screenshot
with ADBBlitz(serial=serial) as ab:
    ab.save_screencap("screenshot.png")
    print(f"Screenshot saved! ({ab.width}x{ab.height})")
```

## Features

- **High Performance**: ~10x faster than standard ADB screencap (~40ms vs ~500ms per frame)
- **Continuous Streaming**: Background thread maintains H264 video stream via adbnativeblitz
- **Low Latency**: Frames available immediately from buffer
- **Cross-Platform**: Full Windows and Linux support (via WSL)
- **Flexible API**: Both single-frame and streaming interfaces
- **No Installation Required**: No need to push binaries or APKs to device
- **Simple Integration**: Wraps adbnativeblitz with consistent MSC API

## Installation

```bash
# Install from workspace
cd msc
uv sync
```

## Requirements

- Python >=3.9
- Android device with ADB enabled
- ADB with `screenrecord` support (Android API 19+)

## Dependencies

- `adbutils>=2.8.0` - ADB communication
- `adbnativeblitz` - Native H264 streaming implementation
- `opencv-python-headless>=4.11.0.86` - Image processing
- `loguru>=0.7.3` - Logging

## Usage

### Basic Usage

```python
from msc.adbblitz import ADBBlitz

# Create instance
ab = ADBBlitz(serial="127.0.0.1:5555")

# Capture single frame
image = ab.screencap()  # Returns cv2.Mat (BGR format)

# Get raw bytes (RGBA format)
raw_data = ab.screencap_raw()  # Returns bytes

# Save screenshot to file
ab.save_screencap("screenshot.png")

# Cleanup
ab.close()
```

**Important**: The first `screencap()` call may take 1-2 seconds as the H264 stream initializes. Subsequent calls are much faster (~40ms).

### Context Manager (Recommended)

```python
# Automatic cleanup with context manager
with ADBBlitz(serial="127.0.0.1:5555") as ab:
    image = ab.screencap()
    ab.save_screencap("screenshot.png")
    # Automatic cleanup on exit
```

### Streaming Mode

For continuous capture at high frame rates:

```python
import cv2
from msc.adbblitz import ADBBlitz

with ADBBlitz(serial="127.0.0.1:5555") as ab:
    for frame in ab:
        cv2.imshow("Screen", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
```

### Custom Configuration

```python
ab = ADBBlitz(
    serial="127.0.0.1:5555",
    width=1280,           # Target width (None = device width)
    height=720,           # Target height (None = device height)
    bitrate="20M",        # Video bitrate (e.g., "20M" for 20Mbps)
    buffer_size=10,       # Frame buffer size (default: 10 frames)
    time_interval=179,    # Recording time limit in seconds (max 180)
    go_idle=0,            # Idle time when no frames (higher = less CPU)
)
```

## Performance

Typical performance on a modern Android device:

- **Latency**: 30-60ms per frame (average ~40ms)
- **Throughput**: 15-30 FPS (continuous capture)
- **Initialization**: 1-3 seconds (H264 stream startup)
- **First Frame**: 500-1500ms (initial buffering)
- **Stability**: Very high (std dev < 5ms)

Comparison with other backends:

| Backend | Avg Latency | FPS | Installation | Notes |
|---------|-------------|-----|--------------|-------|
| **ADBBlitz** | **~40ms** | **20-30** | **None** | **Best balance** |
| ADBCap | ~500ms | 2-5 | None | Slowest, most compatible |
| MiniCap | ~35ms | 25-30 | Binary required | Fastest, limited SDK support |
| DroidCast | ~90ms | 10-15 | APK required | Good for remote viewing |

> **Note**: Run `python performance_test.py` to benchmark on your device.

## How It Works

The implementation uses the [adbnativeblitz](https://github.com/hansalemaos/adbnativeblitz) library which provides:

1. **Native Integration**: Direct use of ADB's screenrecord command
2. **H264 Streaming**: Continuous H264 video stream from device
3. **Efficient Decoding**: Native H264 codec parsing and decoding
4. **Frame Buffering**: Circular buffer for recent frames
5. **High Performance**: Optimized for minimal latency and high throughput

## Architecture

```
┌─────────────────────────────────────┐
│         ADBBlitz Class              │
├─────────────────────────────────────┤
│ User API:                          │
│  - screencap() → latest frame       │
│  - screencap_raw() → latest bytes   │
│  - __iter__() → stream frames       │
├─────────────────────────────────────┤
│ adbnativeblitz Library:            │
│  - Native H264 stream handling      │
│  - Efficient frame decoding         │
│  - Circular frame buffer            │
│  - Background thread management     │
├─────────────────────────────────────┤
│ ADB:                               │
│  - adb shell screenrecord           │
│  - --output-format=h264             │
└─────────────────────────────────────┘
```

## Testing

### Unit Tests (No Device Required)

```bash
# Run all unit tests with mocking
pytest -v -m unit msc-adbblitz/tests/
```

All unit tests use mocking and don't require a physical device.

### E2E Tests (Device Required)

```bash
# Run all E2E tests (requires connected Android device)
pytest -v -m e2e msc-adbblitz/tests/

# Run all tests (unit + E2E)
pytest -v msc-adbblitz/tests/

# Skip E2E tests (unit tests only)
pytest -v -m "not e2e" msc-adbblitz/tests/
```

### Quick Functional Tests

For quick manual testing with a real device:

```bash
# Quick test all backends (saves screenshots)
python test.py

# Comprehensive ADBBlitz test (4 test cases)
python test_adbblitz.py

# Full performance benchmark
python performance_test.py

# Custom benchmark
python performance_test.py --iterations 100 --warmup 5
```

**test_adbblitz.py** includes:
1. Basic screenshot capture
2. Performance test (10 iterations)
3. Streaming iterator test
4. Raw bytes conversion test

Expected output:
```
✓ 测试 1: 基本截图功能 (45ms)
✓ 测试 2: 连续截图性能测试 (avg: 41ms, FPS: 24)
✓ 测试 3: 流式迭代器测试 (5 frames, FPS: 23)
✓ 测试 4: 原始字节数据测试 (RGBA format)
✓ 所有测试通过!
```

## Troubleshooting

### No frames available

**Problem**: No frames or capture stops

**Possible causes**:
1. Device doesn't support H264 output format
2. Custom resolution not supported by device
3. ADB connection issues
4. Recording time limit reached (time_interval)

**Solutions**:
```python
# Try with default resolution (most compatible)
ab = ADBBlitz(serial="...")  # Don't specify width/height

# Increase time_interval (max 180 seconds)
ab = ADBBlitz(serial="...", time_interval=179)

# Or use standard ADB screencap as fallback
from msc.adbcap import ADBCap
ab = ADBCap(serial="...")
```

### Low frame rate

**Problem**: Streaming is slow or choppy

**Solutions**:
- Reduce resolution: `ADBBlitz(width=640, height=480)`
- Lower bitrate: `ADBBlitz(bitrate="4M")`  # 4Mbps
- Increase go_idle: `ADBBlitz(go_idle=0.01)`  # Reduce CPU usage
- Check device CPU usage
- Ensure good USB/network connection

### Memory usage

**Problem**: High memory consumption

**Solution**: Reduce buffer size:

```python
ab = ADBBlitz(buffer_size=10)  # Keep only 10 frames
```

## Limitations

- **Android Version**: Requires Android API 19+ (Android 4.4+) for `screenrecord` support
- **H264 Support**: Some devices may not support H264 output format
- **Custom Resolution**: May not work on all devices - some ignore `--size` parameter or fail to start
  - Recommendation: Use default device resolution for maximum compatibility
- **Initialization Delay**: First frame takes 1-2 seconds (H264 stream startup)
- **Time Limit**: Streams auto-restart after `time_interval` (default 179s, max 180s)
- **CPU Usage**: Continuous streaming increases device CPU usage
- **Memory**: Frame buffer uses memory proportional to resolution × buffer_size

## Implementation Details

This package is a wrapper around [adbnativeblitz](https://github.com/hansalemaos/adbnativeblitz) that:

1. Provides MSC-compatible API (`screencap()`, `screencap_raw()`, `save_screencap()`)
2. Handles device resolution detection automatically
3. Implements context manager protocol for proper cleanup
4. Adds streaming iterator support (`for frame in ab`)

The actual H264 streaming and decoding is handled by adbnativeblitz, which uses:
- ADB's `screenrecord --output-format=h264` command
- Native H264 codec parsing and frame decoding
- Efficient circular frame buffer
- Background thread for continuous stream processing

## Credits

- Based on [adbnativeblitz](https://github.com/hansalemaos/adbnativeblitz) by hansalemaos
- Part of the [MSC (Mobile Screenshot Capture)](https://github.com/yourusername/msc) framework

## License

Same as parent project.

## See Also

- [MSC Framework](../../README.md) - Parent project documentation
- [test_adbblitz.py](../../test_adbblitz.py) - Comprehensive test suite
- [performance_test.py](../../performance_test.py) - Performance benchmarking
- [ADBBLITZ_E2E_TESTS.md](../../ADBBLITZ_E2E_TESTS.md) - Testing guide
