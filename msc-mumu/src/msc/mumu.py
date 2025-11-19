import ctypes
import os

import cv2
import numpy as np
from mmumu.api import MuMuApi
from mmumu.base import get_mumu_path

from msc.screencap import ScreenCap


class MuMuCap(ScreenCap):
    """Screen capture implementation for MuMu emulator using external_renderer_ipc.dll."""

    MUMU_API_DLL_PATH = os.path.join("shell", "sdk", "external_renderer_ipc.dll")
    MUMU_12_5_API_DLL_PATH = os.path.join(
        "nx_device", "12.0", "shell", "sdk", "external_renderer_ipc.dll"
    )

    def __init__(
        self,
        instance_index: int,
        emulator_install_path: str = None,
        dll_path: str = None,
        display_id: int = 0,
    ):
        """
        Initialize MuMu screen capture.

        Args:
            instance_index: Emulator instance index.
            emulator_install_path: Emulator installation path. If None, it will be
                resolved via the registry using get_mumu_path().
            dll_path: Optional path to external_renderer_ipc.dll. If None it will
                be resolved from the emulator installation path.
            display_id: Display window id. Usually 0.
        """
        self.display_id = display_id
        self.instance_index = instance_index
        self.emulator_install_path = emulator_install_path or get_mumu_path()

        uninstall_exe = os.path.join(self.emulator_install_path, "uninstall.exe")
        if not os.path.exists(uninstall_exe):
            raise FileNotFoundError(
                "MuMu uninstall.exe not found; emulator installation path is invalid"
            )

        self.dllPath = dll_path or os.path.join(
            self.emulator_install_path, self.MUMU_API_DLL_PATH
        )
        if not os.path.exists(self.dllPath):
            self.dllPath = os.path.join(
                self.emulator_install_path, self.MUMU_12_5_API_DLL_PATH
            )
        if not os.path.exists(self.dllPath):
            raise FileNotFoundError("external_renderer_ipc.dll not found")

        self.width: int
        self.height: int
        self.buffer_size: int

        self.nemu = MuMuApi(self.dllPath)
        # Connect to emulator
        self.handle = self.nemu.connect(self.emulator_install_path, self.instance_index)
        self.__get_display_info()

    def __get_display_info(self) -> None:
        """Query display size and allocate pixel buffer."""
        width = ctypes.c_int(0)
        height = ctypes.c_int(0)
        result = self.nemu.capture_display(
            self.handle,
            self.display_id,
            0,
            ctypes.byref(width),
            ctypes.byref(height),
            None,
        )
        if result != 0:
            raise RuntimeError(f"Failed to get display size, result code: {result}")

        self.width, self.height = width.value, height.value
        self.buffer_size = self.width * self.height * 4
        self.pixels = (ctypes.c_ubyte * self.buffer_size)()

    def __buffer2opencv(self) -> cv2.Mat:
        """Convert the internal pixel buffer to an OpenCV BGR image."""
        pixel_array = np.frombuffer(
            self.pixels, dtype=np.uint8
        ).reshape((self.height, self.width, 4))
        # Flip vertically if MuMu provides an upside-down image
        pixel_array = pixel_array[::-1, :, :]
        # Convert from RGBA to BGR (same as ADBCap)
        return cv2.cvtColor(pixel_array, cv2.COLOR_RGBA2BGR)

    def close(self) -> None:
        """Disconnect from the emulator."""
        nemu = getattr(self, "nemu", None)
        handle = getattr(self, "handle", None)
        if nemu is not None and handle is not None:
            try:
                nemu.disconnect(handle)
            except Exception:
                pass
            # Clear handle to prevent double disconnection
            self.handle = None

    def __del__(self) -> None:
        self.close()

    def screencap(self) -> cv2.Mat:
        result = self.nemu.capture_display(
            self.handle,
            self.display_id,
            self.buffer_size,
            ctypes.c_int(self.width),
            ctypes.c_int(self.height),
            self.pixels,
        )
        if result > 1:
            raise BufferError("Failed to capture screen")
        return self.__buffer2opencv()

    def screencap_raw(self) -> bytes:
        """Return raw RGBA bytes from MuMu shared memory."""
        result = self.nemu.capture_display(
            self.handle,
            self.display_id,
            self.buffer_size,
            ctypes.c_int(self.width),
            ctypes.c_int(self.height),
            self.pixels,
        )
        if result > 1:
            raise BufferError("Failed to capture screen")
        return bytes(self.pixels)


if __name__ == "__main__":
    import time

    d = MuMuCap(0)
    s = time.time()
    np_arr = d.screencap()
    print((time.time() - s) * 1000)
    cv2.imshow("", np_arr)
    cv2.waitKey(0)
