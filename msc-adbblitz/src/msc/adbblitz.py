from typing import Iterator, Optional

import cv2
from adbutils import adb, adb_path
from adbnativeblitz import AdbFastScreenshots
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
        time_interval: int = 179,
        width: Optional[int] = None,
        height: Optional[int] = None,
        bitrate: str = "20M",
        buffer_size: int = 10,
        go_idle: float = 0,
    ):
        """
        Initialize ADBBlitz screen capture.

        Args:
            serial: Device serial number
            time_interval: Time limit for recording in seconds (max 180)
            width: Target width (None = device width)
            height: Target height (None = device height)
            bitrate: Video bitrate for H264 encoding (e.g., "20M" for 20Mbps)
            buffer_size: Frame buffer size (number of frames to keep)
            go_idle: Idle time in seconds when no new frames available (higher = less CPU)
        """
        self.serial = serial
        self.adb_device = adb.device(serial)

        # Get device dimensions if not specified
        if width is None or height is None:
            device_width, device_height = self.adb_device.window_size()
            self.width = width or device_width
            self.height = height or device_height
        else:
            self.width = width
            self.height = height

        logger.info(
            f"Initializing ADBBlitz: serial={serial}, resolution={self.width}x{self.height}, "
            f"bitrate={bitrate}, buffer_size={buffer_size}"
        )

        # Initialize adbnativeblitz
        self.adb_screenshots = AdbFastScreenshots(
            adb_path=adb_path(),
            device_serial=serial,
            time_interval=time_interval,
            width=self.width,
            height=self.height,
            bitrate=bitrate,
            use_busybox=False,
            connect_to_device=False,  # Already connected
            screenshotbuffer=buffer_size,
            go_idle=go_idle,
        )

        # Iterator for frame access
        self._frame_iterator = None

        logger.info("ADBBlitz initialized successfully")

    def _get_frame_iterator(self) -> Iterator[cv2.Mat]:
        """Get or create the frame iterator."""
        if self._frame_iterator is None:
            self._frame_iterator = iter(self.adb_screenshots)
        return self._frame_iterator

    def screencap(self) -> cv2.Mat:
        """
        Get latest frame as OpenCV Mat (BGR format).

        Returns:
            cv2.Mat: BGR format image

        Raises:
            StopIteration: If the capture has stopped
        """
        try:
            return next(self._get_frame_iterator())
        except StopIteration:
            logger.error("Frame capture stopped")
            raise RuntimeError("Frame capture has stopped")

    def screencap_raw(self) -> bytes:
        """
        Get latest frame as raw bytes.

        Returns:
            bytes: Raw RGBA bytes
        """
        frame = self.screencap()

        # Convert BGR NumPy array to RGBA bytes to match other backends
        rgba_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        return rgba_frame.tobytes()

    def __iter__(self) -> Iterator[cv2.Mat]:
        """
        Iterate over frames as they arrive (streaming mode).

        Yields:
            cv2.Mat: Each frame as it becomes available
        """
        return self._get_frame_iterator()

    def close(self) -> None:
        """Stop capture and release resources."""
        logger.info("Stopping ADBBlitz capture")

        if self.adb_screenshots:
            self.adb_screenshots.stop_capture()

        logger.info("ADBBlitz capture stopped")

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
        return False
