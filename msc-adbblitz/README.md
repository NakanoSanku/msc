# msc-adbblitz

High-performance ADB screenshot backend using H264 streaming.

## Overview

`msc-adbblitz` provides ultra-fast screenshot capture for Android devices by leveraging ADB's `screenrecord` command with H264 video streaming. Unlike traditional ADB screencap methods that capture single PNG images, ADBBlitz maintains a continuous H264 video stream, allowing for low-latency frame capture.

Based on the [adbnativeblitz](https://github.com/hansalemaos/adbnativeblitz) library, this implementation integrates seamlessly with the `msc` screenshot backend architecture.

## Features

- **High Performance**: ~10x faster than standard ADB screencap (~50ms vs ~500ms per frame)
- **Continuous Streaming**: Background thread maintains H264 video stream
- **Low Latency**: Frames available immediately from buffer
- **Cross-Platform**: Full Windows and Linux support
- **Flexible API**: Both single-frame and streaming interfaces
- **Thread-Safe**: Proper synchronization for concurrent access

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
- `av>=13.1.0` - H264 codec parsing (pyAV)
- `opencv-python-headless>=4.11.0.86` - Image processing
- `numpy>=1.24.0` - Array operations
- `loguru>=0.7.3` - Logging

## Usage

### Basic Usage

```python
from msc.adbblitz import ADBBlitz

# Create instance (automatically waits for first frame)
ab = ADBBlitz(serial="127.0.0.1:5555")

# Capture single frame (auto-waits up to 5 seconds for first frame)
image = ab.screencap()  # Returns cv2.Mat (BGR format)

# Get raw bytes
raw_data = ab.screencap_raw()  # Returns RGBA bytes

# Save screenshot
ab.save_screencap("screenshot.png")

# Cleanup
ab.close()
```

### Context Manager

```python
# Recommended: Automatic cleanup
with ADBBlitz(serial="127.0.0.1:5555") as ab:
    image = ab.screencap()  # Auto-waits for first frame
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
    bitrate=8000000,      # Video bitrate in bps (default: 8Mbps)
    buffer_size=50,       # Frame buffer size (default: 50 frames)
    time_interval=0,      # Recording time limit (0 = infinite)
)
```

## Performance

Typical performance on a modern Android device:

- **Latency**: <50ms per frame
- **Throughput**: 30-60 FPS
- **Memory**: ~200MB for 1080p with 50-frame buffer

Comparison with other backends:

| Backend | Latency | Throughput | Installation |
|---------|---------|------------|--------------|
| ADBBlitz | ~50ms | 30-60 FPS | None |
| ADBCap | ~500ms | 2-5 FPS | None |
| DroidCast | ~100ms | 15-30 FPS | APK required |
| MiniCap | ~50ms | 30-60 FPS | Binary required |

## How It Works

1. **Subprocess**: Spawns `adb shell screenrecord --output-format=h264`
2. **H264 Stream**: Reads raw H264 video data from stdout
3. **Codec Parsing**: Uses pyAV to parse and decode H264 packets
4. **Frame Buffer**: Maintains circular buffer of recent frames
5. **API**: Provides latest frame on demand via `screencap()`

## Architecture

```
┌─────────────────────────────────────┐
│         ADBBlitz Class              │
├─────────────────────────────────────┤
│ Main Thread (User API):            │
│  - screencap() → latest frame       │
│  - screencap_raw() → latest bytes   │
│  - __iter__() → stream frames       │
├─────────────────────────────────────┤
│ Background Thread:                  │
│  - Read screenrecord stdout         │
│  - Parse H264 with pyAV             │
│  - Decode to BGR24 NumPy            │
│  - Update deque buffer              │
├─────────────────────────────────────┤
│ Subprocess:                         │
│  - adb shell screenrecord           │
│  - --output-format=h264             │
└─────────────────────────────────────┘
```

## Testing

```bash
# Run all tests
pytest -v msc-adbblitz/tests/

# Run only unit tests (no device required)
pytest -v -m unit msc-adbblitz/tests/

# Run only E2E tests (requires connected device)
pytest -v -m e2e msc-adbblitz/tests/

# Skip E2E tests
pytest -v -m "not e2e" msc-adbblitz/tests/
```

## Troubleshooting

### No frames available after timeout

**Problem**: `RuntimeError: No frames available after 5s`

**Possible causes**:
1. Device doesn't support H264 output format
2. Custom resolution not supported by device
3. ADB connection issues

**Solutions**:
```python
# Try with default resolution (most compatible)
ab = ADBBlitz(serial="...")  # Don't specify width/height

# Or use standard ADB screencap as fallback
from msc.adbcap import ADBCap
ab = ADBCap(serial="...")
```

### Low frame rate

**Problem**: Streaming is slow or choppy

**Solutions**:
- Reduce resolution: `ADBBlitz(width=640, height=480)`
- Lower bitrate: `ADBBlitz(bitrate=4000000)`  # 4Mbps
- Check device CPU usage
- Ensure good USB/network connection

### Memory usage

**Problem**: High memory consumption

**Solution**: Reduce buffer size:

```python
ab = ADBBlitz(buffer_size=10)  # Keep only 10 frames
```

## Limitations

- Requires Android API 19+ (Android 4.4+)
- Some devices may not support H264 output format
- **Custom resolution may not work on all devices** - some devices ignore `--size` parameter or fail to start
- Continuous streaming increases device CPU usage
- Frame buffer uses memory proportional to resolution and buffer size

## Credits

Based on [adbnativeblitz](https://github.com/hansalemaos/adbnativeblitz) by hansalemaos.

## License

Same as parent project.
