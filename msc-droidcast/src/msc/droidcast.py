import os.path
import subprocess
import time
from typing import Optional

import cv2
import numpy as np
import requests
from adbutils import adb, adb_path
from loguru import logger

from msc.screencap import ScreenCap


class DroidCast(ScreenCap):
    APK_PACKAGE_NAME = "com.rayworks.droidcast"
    PM_PATH_SHELL = f"pm path {APK_PACKAGE_NAME}"
    START_CMD = f"exec app_process / {APK_PACKAGE_NAME}.Main"
    APK_NAME_PREFIX = "DroidCast_"
    APK_VERSION = "1.4.1"
    APK_PATH = os.path.join(
        os.path.dirname(__file__),
        "bin",
        f"{APK_NAME_PREFIX}{APK_VERSION}.apk",
    )
    APK_ANDROID_PATH = f"/data/local/tmp/{APK_NAME_PREFIX}{APK_VERSION}.apk"
    MAX_RETRY = 3
    RETRY_DELAY = 0.5

    def __init__(
        self,
        serial: str,
        display_id: Optional[int] = None,
        port: int = 53516,
        timeout: int = 3,
    ):
        """
        Initialize DroidCast screen capture.

        Args:
            serial: device id.
            display_id: display id (use
                `adb shell dumpsys SurfaceFlinger --display-id` to get).
            port: DroidCast listen port on device.
            timeout: HTTP request timeout (seconds).
        """
        self.adb = adb.device(serial)
        self.display_id: Optional[int] = display_id
        self.remote_port = port
        self.timeout = timeout

        # Runtime state
        self.session = requests.Session()
        self.popen: Optional[subprocess.Popen] = None
        self.local_port: Optional[int] = None
        self.url: Optional[str] = None

        # Expected buffer size based on current window size
        self.width, self.height = self.adb.window_size()
        self.buffer_size = self.width * self.height * 4

        # Install and start DroidCast process
        self.install()
        self.start()

    def install(self) -> None:
        """Ensure the expected DroidCast APK version is installed."""
        if self.APK_PACKAGE_NAME not in self.adb.list_packages():
            logger.info(
                f"Installing {self.APK_PACKAGE_NAME} {self.APK_VERSION} from {self.APK_PATH}"
            )
            self.adb.install(self.APK_PATH, nolaunch=True)
        else:
            version_name = self.adb.package_info(self.APK_PACKAGE_NAME)["version_name"]
            if version_name != self.APK_VERSION:
                logger.info(
                    f"Upgrading {self.APK_PACKAGE_NAME} "
                    f"from {version_name} to {self.APK_VERSION}"
                )
                self.adb.uninstall(self.APK_PACKAGE_NAME)
                self.adb.install(self.APK_PATH, nolaunch=True)

    def open_popen(self) -> None:
        """Start DroidCast via adb shell app_process."""
        pm_output = self.adb.shell(self.PM_PATH_SHELL).strip()
        if not pm_output or ":" not in pm_output:
            logger.error(
                f"Failed to get pm path for {self.APK_PACKAGE_NAME}: {pm_output}"
            )
            raise RuntimeError(
                f"Cannot determine CLASSPATH for {self.APK_PACKAGE_NAME}, "
                f"pm output: {pm_output}"
            )

        # Example pm_output: "package:/data/app/~~xxxx/base.apk"
        class_path = "CLASSPATH=" + pm_output.split(":", 1)[1]

        adb_command = [
            adb_path(),
            "-s",
            self.adb.serial,
            "shell",
            class_path,
            self.START_CMD,
        ]
        adb_command.append(f"--port={self.remote_port}")
        if self.display_id is not None:
            adb_command.append(f"--display_id={self.display_id}")

        logger.info(f"Starting DroidCast with command: {adb_command}")

        self.popen = subprocess.Popen(
            adb_command,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )

    def forward_port(self) -> None:
        """Forward a local TCP port to the DroidCast port on device."""
        if self.local_port is None:
            # Use a fixed port to avoid WSL/Windows port binding conflicts
            fixed_port = 37516  # Fixed port for DroidCast
            try:
                self.adb.forward(f"tcp:{fixed_port}", f"tcp:{self.remote_port}")
                self.local_port = fixed_port
                logger.info(
                    f"Using fixed port {fixed_port} forwarding to remote port {self.remote_port}"
                )
            except Exception as e:
                # If fixed port fails, fall back to dynamic port
                logger.warning(f"Fixed port {fixed_port} failed: {e}, trying dynamic port")
                self.local_port = self.adb.forward_port(self.remote_port)
                logger.info(
                    f"Forwarded local port {self.local_port} "
                    f"to remote port {self.remote_port}"
                )
            self.url = f"http://localhost:{self.local_port}/screenshot?format=raw"

    def start(self) -> None:
        """Start DroidCast process if needed."""
        self.forward_port()
        self.open_popen()
        logger.info("DroidCast started")

    def stop(self) -> None:
        """Stop the adb shell process if still running."""
        if self.popen is not None and self.popen.poll() is None:
            self.popen.kill()
            logger.info("DroidCast process stopped")

    def restart(self) -> None:
        """Restart the DroidCast process."""
        self.stop()
        self.open_popen()
        logger.info("DroidCast process restarted")

    def close(self) -> None:
        """Stop DroidCast and release resources."""
        self.stop()
        try:
            self.session.close()
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()

    def screencap_raw(self) -> bytes:
        """Return raw RGBA bytes from DroidCast HTTP endpoint."""
        if self.url is None:
            self.forward_port()

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                assert self.url is not None
                response = self.session.get(self.url, timeout=self.timeout)
                response.raise_for_status()
                return response.content
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = exc
                logger.warning(
                    "DroidCast screenshot connection failed on attempt "
                    f"{attempt}/{self.MAX_RETRY}: {exc}"
                )
                self.restart()
                time.sleep(self.RETRY_DELAY)
            except requests.exceptions.HTTPError as exc:
                last_exc = exc
                logger.warning(
                    "DroidCast screenshot HTTP error on attempt "
                    f"{attempt}/{self.MAX_RETRY}: {exc}"
                )
                time.sleep(self.RETRY_DELAY)

        raise RuntimeError(
            f"Failed to get screenshot from DroidCast after {self.MAX_RETRY} attempts"
        ) from last_exc

    def screencap(self) -> cv2.Mat:
        """Return an OpenCV BGR image for the current screen."""
        raw = self.screencap_raw()

        # If the device resolution changed since init, try to adapt.
        if len(raw) < self.buffer_size:
            width, height = self.adb.window_size()
            buffer_size = width * height * 4
            if len(raw) < buffer_size:
                raise ValueError(
                    f"Raw data length {len(raw)} is less than expected {self.buffer_size}"
                )
            self.width, self.height, self.buffer_size = width, height, buffer_size

        arr = np.frombuffer(raw[: self.buffer_size], np.uint8).reshape(
            (self.height, self.width, 4)
        )

        # Convert from RGBA to OpenCV BGR
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
