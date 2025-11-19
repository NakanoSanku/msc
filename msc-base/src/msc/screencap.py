from abc import ABC, abstractmethod
from typing import Optional, Type
from types import TracebackType

import cv2

class ScreenCap(ABC):

    @abstractmethod
    def screencap_raw(self) -> bytes:
        """
        获取屏幕截图的原始数据。
        
        Returns:
            bytes: 原始图像数据。具体格式取决于实现（通常为 RGBA 或 RGB）。
        """

    @abstractmethod
    def screencap(self) -> cv2.Mat:
        """
        获取 OpenCV 格式的屏幕截图。
        
        Returns:
            cv2.Mat: BGR 格式的图像数据。
        """

    def save_screencap(self, filename="screencap.png"):
        """
        save_screencap 保存截图

        Args:
            filename (str, optional): 截图保存路径. Defaults to "screencap.png".
        """
        cv2.imwrite(filename, self.screencap())

    def close(self) -> None:
        """释放资源"""
        pass

    def __enter__(self) -> "ScreenCap":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()



