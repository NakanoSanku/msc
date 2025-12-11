import platform
import subprocess
import threading
from collections import deque
from typing import Iterator, Optional

import av
import cv2
import numpy as np
from adbutils import adb, adb_path
from loguru import logger

from msc.screencap import ScreenCap


class ADBBlitz(ScreenCap):
    """
    High-performance ADB screenshot using H264 streaming.

    Based on adbnativeblitz library, this implementation uses ADB's
    screenrecord with H264 output format for continuous low-latency
    frame capture.
    """

    def __init__(
        self,
        serial: str,
        time_interval: float = 0.0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        bitrate: int = 8000000,
        buffer_size: int = 50,
    ):
        """
        Initialize ADBBlitz screen capture.

        Args:
            serial: Device serial number
            time_interval: Time limit for recording (0 = infinite)
            width: Target width (None = device width)
            height: Target height (None = device height)
            bitrate: Video bitrate for H264 encoding (default: 8Mbps)
            buffer_size: Frame buffer size (number of frames to keep)
        """
        self.adb = adb.device(serial)
        self.time_interval = time_interval
        self.bitrate = bitrate
        self.buffer_size = buffer_size

        # Get device dimensions
        device_width, device_height = self.adb.window_size()
        self.width = width or device_width
        self.height = height or device_height

        # Initialize H264 codec context
        self.codec = av.codec.CodecContext.create("h264", "r")

        # Frame buffer: deque for thread-safe circular buffer
        self.frame_buffer: deque = deque(maxlen=buffer_size)
        self.frame_lock = threading.Lock()

        # Thread management
        self.stop_event = threading.Event()
        self.capture_thread: Optional[threading.Thread] = None
        self.process: Optional[subprocess.Popen] = None

        # Start capture
        self._start_capture()

    def _start_capture(self) -> None:
        """Start the background capture process and thread."""
        # Build screenrecord command
        cmd_parts = [
            adb_path(),
            "-s",
            self.adb.serial,
            "shell",
            "screenrecord",
            "--output-format=h264",
            f"--bit-rate={self.bitrate}",
        ]

        if self.width and self.height:
            cmd_parts.extend([f"--size={self.width}x{self.height}"])

        if self.time_interval > 0:
            cmd_parts.extend([f"--time-limit={int(self.time_interval)}"])

        cmd_parts.append("-")  # Output to stdout

        logger.info(f"Starting ADBBlitz capture: {' '.join(cmd_parts)}")

        # Platform-specific subprocess configuration
        startupinfo = None
        creationflags = 0
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        # Start subprocess
        self.process = subprocess.Popen(
            cmd_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=creationflags,
            bufsize=0,
        )

        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="ADBBlitz-CaptureThread"
        )
        self.capture_thread.start()

        logger.info("ADBBlitz capture started")

    def _capture_loop(self) -> None:
        """Background thread: read H264 stream and decode frames."""
        buffer = bytearray()

        try:
            while not self.stop_event.is_set() and self.process:
                # Read data from subprocess
                chunk = self.process.stdout.read(4096)
                if not chunk:
                    logger.warning("ADBBlitz: stdout closed")
                    break

                buffer.extend(chunk)

                # Parse H264 packets
                try:
                    packets = self.codec.parse(bytes(buffer))
                    buffer.clear()  # Clear after successful parse

                    for packet in packets:
                        # Decode packet to frames
                        frames = self.codec.decode(packet)
                        for frame in frames:
                            # Convert to BGR24 NumPy array
                            # Don't force resize - use actual decoded frame size
                            bgr_frame = (
                                frame.to_rgb()
                                .reformat(format="bgr24")
                                .to_ndarray()
                            )

                            # Update actual dimensions from first frame
                            if bgr_frame.shape[0] != self.height or bgr_frame.shape[1] != self.width:
                                logger.info(
                                    f"Actual frame size {bgr_frame.shape[1]}x{bgr_frame.shape[0]} "
                                    f"differs from expected {self.width}x{self.height}, updating"
                                )
                                self.height, self.width = bgr_frame.shape[:2]
                                self.buffer_size = self.width * self.height * 4

                            # Add to buffer (thread-safe)
                            with self.frame_lock:
                                self.frame_buffer.append(bgr_frame)

                except av.AVError as e:
                    logger.debug(f"H264 parse error (may need more data): {e}")
                    # Keep buffer and wait for more data
                except Exception as e:
                    logger.error(f"Error decoding frame: {e}")
        except Exception as e:
            logger.error(f"ADBBlitz capture loop error: {e}")
        finally:
            logger.info("ADBBlitz capture loop exiting")

    def _get_latest_frame(self, timeout: float = 5.0) -> cv2.Mat:
        """
        Get the most recent frame from buffer.

        Args:
            timeout: Maximum time to wait for first frame (seconds)

        Raises:
            RuntimeError: If no frames available after timeout
        """
        import time

        start_time = time.time()

        # Wait for first frame if buffer is empty
        while not self.frame_buffer:
            if time.time() - start_time > timeout:
                raise RuntimeError(
                    f"No frames available after {timeout}s. "
                    "Check if device supports H264 screenrecord or try default resolution."
                )
            time.sleep(0.05)  # Check every 50ms

            # Check if capture thread died
            if self.capture_thread and not self.capture_thread.is_alive():
                raise RuntimeError(
                    "Capture thread terminated unexpectedly. "
                    "Device may not support the specified parameters."
                )

        with self.frame_lock:
            return self.frame_buffer[-1].copy()  # Return copy for thread safety

    def screencap_raw(self) -> bytes:
        """
        Get latest frame as raw bytes.

        Returns:
            bytes: Raw RGBA bytes
        """
        frame = self._get_latest_frame()

        # Convert BGR NumPy array to RGBA bytes to match other backends
        rgba_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        return rgba_frame.tobytes()

    def screencap(self) -> cv2.Mat:
        """
        Get latest frame as OpenCV Mat (BGR format).

        Returns:
            cv2.Mat: BGR format image
        """
        return self._get_latest_frame()

    def __iter__(self) -> Iterator[cv2.Mat]:
        """
        Iterate over frames as they arrive (streaming mode).

        Yields:
            cv2.Mat: Each frame as it becomes available
        """
        last_count = 0

        while not self.stop_event.is_set():
            with self.frame_lock:
                current_count = len(self.frame_buffer)
                if current_count > last_count and self.frame_buffer:
                    # New frame available
                    yield self.frame_buffer[-1].copy()
                    last_count = current_count

            # Small sleep to prevent busy waiting
            threading.Event().wait(0.01)

    def close(self) -> None:
        """Stop capture and release resources."""
        logger.info("Stopping ADBBlitz capture")

        # Signal thread to stop
        self.stop_event.set()

        # Kill subprocess
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

        # Wait for thread
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)

        # Clear buffer
        with self.frame_lock:
            self.frame_buffer.clear()

        logger.info("ADBBlitz capture stopped")

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except Exception:
            pass
