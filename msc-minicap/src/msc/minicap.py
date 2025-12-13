import json
import os.path
import socket
import subprocess
import threading
import time
from typing import Optional

import cv2
import numpy as np
from adbutils import adb, adb_path
from loguru import logger

from msc.screencap import ScreenCap


class MiniCapStream:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.data: Optional[bytes] = None
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.read_stream, daemon=True)
        self.data_available = threading.Condition()

    def start(self) -> None:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
        except ConnectionRefusedError:
            logger.error(
                f"Be sure to run `adb forward tcp:{self.port} localabstract:minicap`"
            )
            return
        self.thread.start()

    def read_stream(self) -> None:
        banner = {
            "version": 0,
            "length": 0,
            "pid": 0,
            "realWidth": 0,
            "realHeight": 0,
            "virtualWidth": 0,
            "virtualHeight": 0,
            "orientation": 0,
            "quirks": 0,
        }

        read_banner_bytes = 0
        banner_length = 2
        frame_body = bytearray()
        # 每帧固定为 virtualWidth * virtualHeight * 4 字节的 RGBA 数据
        frame_body_length: Optional[int] = None
        max_buf_size = 4096

        try:
            while not self.stop_event.is_set():
                try:
                    assert self.sock is not None
                    chunk = self.sock.recv(max_buf_size)
                    if not chunk:
                        # socket 已关闭
                        break
                except OSError as e:
                    # Windows 下主动关闭 socket 会触发 WinError 10053/10054
                    if e.errno in (10053, 10054) or "WinError 10053" in str(e):
                        logger.info("Socket closed, stopping read_stream gracefully")
                        break
                    raise

                cursor = 0
                while cursor < len(chunk):
                    if read_banner_bytes < banner_length:
                        # 解析 banner（参考 minicap 协议）
                        byte = chunk[cursor]
                        if read_banner_bytes == 0:
                            banner["version"] = byte
                        elif read_banner_bytes == 1:
                            banner["length"] = banner_length = byte
                        elif 2 <= read_banner_bytes <= 5:
                            banner["pid"] += (
                                byte << ((read_banner_bytes - 2) * 8)
                            ) & 0xFFFFFFFF
                        elif 6 <= read_banner_bytes <= 9:
                            banner["realWidth"] += (
                                byte << ((read_banner_bytes - 6) * 8)
                            ) & 0xFFFFFFFF
                        elif 10 <= read_banner_bytes <= 13:
                            banner["realHeight"] += (
                                byte << ((read_banner_bytes - 10) * 8)
                            ) & 0xFFFFFFFF
                        elif 14 <= read_banner_bytes <= 17:
                            banner["virtualWidth"] += (
                                byte << ((read_banner_bytes - 14) * 8)
                            ) & 0xFFFFFFFF
                        elif 18 <= read_banner_bytes <= 21:
                            banner["virtualHeight"] += (
                                byte << ((read_banner_bytes - 18) * 8)
                            ) & 0xFFFFFFFF
                        elif read_banner_bytes == 22:
                            banner["orientation"] = byte * 90
                        elif read_banner_bytes == 23:
                            banner["quirks"] = byte

                        cursor += 1
                        read_banner_bytes += 1

                        if read_banner_bytes == banner_length:
                            logger.info(f"banner {banner}")
                    else:
                        # banner 解析完成后开始按固定长度读取 RGBA 帧
                        if frame_body_length is None:
                            vw = banner["virtualWidth"]
                            vh = banner["virtualHeight"]
                            if vw and vh:
                                frame_body_length = vw * vh * 4
                            else:
                                # 未能获取到有效分辨率，跳过本次数据
                                break

                        remaining = len(chunk) - cursor
                        needed = frame_body_length - len(frame_body)
                        to_read = min(remaining, needed)
                        if to_read > 0:
                            frame_body.extend(chunk[cursor : cursor + to_read])
                            cursor += to_read

                        if frame_body_length is not None and len(frame_body) == frame_body_length:
                            # 完整帧就绪，通知等待者
                            with self.data_available:
                                self.data = bytes(frame_body)
                                self.data_available.notify_all()
                            # 重置缓冲，准备下一帧
                            frame_body = bytearray()
        finally:
            logger.info("read_stream thread exiting")

    def stop(self) -> None:
        logger.info("Stopping the stream")
        self.stop_event.set()
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        if self.thread.is_alive():
            self.thread.join()

    def next_image(self) -> bytes:
        with self.data_available:
            while self.data is None or len(self.data) == 0:
                self.data_available.wait()  # 等待数据可用
            return self.data


class MiniCapUnSupportError(Exception):
    pass


class MiniCap(ScreenCap):
    WORK_DIR = os.path.dirname(__file__)
    MINICAP_PATH = f"{WORK_DIR}/bin/minicap/libs"
    MINICAP_SO_PATH = f"{WORK_DIR}/bin/minicap/jni"
    MNC_HOME = "/data/local/tmp/minicap"
    MNC_SO_HOME = "/data/local/tmp/minicap.so"
    MINICAP_COMMAND = [
        "LD_LIBRARY_PATH=/data/local/tmp",
        "/data/local/tmp/minicap",
    ]
    MINICAP_START_TIMEOUT = 3

    def __init__(
        self,
        serial: str,
        rate: Optional[int] = None,
        quality: int = 100,
        skip_frame: bool = True,
        use_stream: bool = True,
    ) -> None:
        """
        __init__ minicap截图方式

        Args:
            serial (str): 设备id
            rate (int, optional): 截图帧率. Defaults to 自动获取.
            quality (int, optional): 截图品质1~100之间. Defaults to 100.
            skip_frame(bool,optional): 当无法快速获得截图时，跳过这个帧
            use_stream (bool, optional): 是否使用stream的方式. Defaults to True.
        """
        # 初始化设备
        self.adb = adb.device(serial)
        self.skip_frame = skip_frame
        self.use_stream = use_stream
        self.quality = quality
        self.rate = rate
        # 初始化设备信息
        self.rotation: Optional[int] = None
        self.vm_size: Optional[str] = None
        self.port: Optional[int] = None
        self.abi = self.adb.getprop("ro.product.cpu.abi")
        self.sdk = self.adb.getprop("ro.build.version.sdk")
        # 记录当前窗口大小，并计算 RGBA 缓冲区长度
        self.width, self.height = self.adb.window_size()
        self.buffer_size = self.width * self.height * 4

        self.kill()  # 杀掉已有 minicap 进程
        self.install()  # 安装 minicap
        self.get_device_input_info()  # 使用 minicap -i 获取参数
        # 启动 minicap stream
        self.popen: Optional[subprocess.Popen] = None
        self.stream: Optional[MiniCapStream] = None
        if self.use_stream:
            self.start_minicap_by_stream()

    def kill(self) -> None:
        self.adb.shell(["pkill", "-9", "minicap"])

    def install(self) -> None:
        """安装 minicap"""
        if str(self.sdk) == "32" and str(self.abi) == "x86_64":
            self.abi = "x86"
        if int(self.sdk) > 34:
            raise MiniCapUnSupportError(f"minicap does not support Android SDK {self.sdk} (Max 34)")
        self.adb.sync.push(f"{self.MINICAP_PATH}/{self.abi}/minicap", self.MNC_HOME)
        self.adb.sync.push(
            f"{self.MINICAP_SO_PATH}/android-{self.sdk}/{self.abi}/minicap.so",
            self.MNC_SO_HOME,
        )
        self.adb.shell(["chmod +x", self.MNC_HOME])

    def get_device_input_info(self) -> None:
        try:
            # 通过 -i 参数获取屏幕信息
            command = self.MINICAP_COMMAND + ["-i"]
            info_result = self.adb.shell(command)
            # 找到 JSON 数据的起始位置
            start_index = info_result.find("{")
            # 提取 JSON 字符串
            if start_index != -1:
                extracted_json = info_result[start_index:]
                logger.info(extracted_json)
            else:
                raise MiniCapUnSupportError("minicap does not support")
            info = json.loads(extracted_json)
            self.vm_size = self.adb.shell("wm size").split(" ")[-1]
            self.rotation = info.get("rotation")
            if self.rate is None:
                self.rate = info.get("fps")
        except Exception as e:  # noqa: BLE001
            raise MiniCapUnSupportError(f"minicap does not support\n{e}") from e

    def start_minicap(self) -> None:
        adb_command = [adb_path(), "-s", self.adb.serial, "shell"]
        adb_command.extend(self.MINICAP_COMMAND)
        adb_command.extend(["-P", f"{self.vm_size}@{self.vm_size}/{self.rotation}"])
        adb_command.extend(["-Q", str(self.quality)])
        adb_command.extend(["-r", str(self.rate)])
        if self.skip_frame:
            adb_command.extend(["-S"])
        logger.info(adb_command)
        # 启动 minicap popen
        self.popen = subprocess.Popen(  # type: ignore[arg-type]
            adb_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("minicap connection takes a long time, please be patient.")
        time.sleep(self.MINICAP_START_TIMEOUT)

    def forward_port(self) -> None:
        # Use a fixed port to avoid WSL/Windows port binding conflicts
        fixed_port = 37468  # Fixed port for minicap
        try:
            self.adb.forward(f"tcp:{fixed_port}", "localabstract:minicap")
            self.port = fixed_port
            logger.info(f"Using fixed port {fixed_port} for minicap")
        except Exception as e:
            # If fixed port fails, fall back to dynamic port
            logger.warning(f"Fixed port {fixed_port} failed: {e}, trying dynamic port")
            self.port = self.adb.forward_port("localabstract:minicap")

    def read_minicap_stream(self) -> None:
        # 会通过 adb 转发到本地端口，所以地址写死 127.0.0.1，端口号为转发得到的端口
        assert self.port is not None
        self.stream = MiniCapStream("127.0.0.1", self.port)
        self.stream.start()

    def start_minicap_by_stream(self) -> None:
        self.start_minicap()
        self.forward_port()
        self.read_minicap_stream()

    def stop_minicap_by_stream(self) -> None:
        if self.use_stream and self.stream is not None:
            self.stream.stop()  # 停止 stream
        if self.popen is not None and self.popen.poll() is None:
            self.popen.kill()

    def close(self) -> None:
        """Stop minicap and release resources."""
        self.stop_minicap_by_stream()

    def __del__(self) -> None:
        self.close()

    def get_minicap_frame(self) -> bytes:
        adb_command = list(self.MINICAP_COMMAND)
        adb_command.extend(["-P", f"{self.vm_size}@{self.vm_size}/{self.rotation}"])
        adb_command.extend(["-Q", str(self.quality)])
        adb_command.extend(["-s"])
        raw_data = self.adb.shell(adb_command, encoding=None)
        return raw_data.split(b"for JPG encoder\n")[-1]

    def screencap_raw(self) -> bytes:
        if self.use_stream:
            assert self.stream is not None
            return self.stream.next_image()
        return self.get_minicap_frame()

    def screencap(self) -> cv2.Mat:
        raw = self.screencap_raw()
        if not raw:
            raise ValueError("Empty frame received from minicap")

        if self.use_stream:
            # 原始 RGBA 数据
            if len(raw) < self.buffer_size:
                raise ValueError(
                    f"Raw data length {len(raw)} is less than expected {self.buffer_size}"
                )
            arr = np.frombuffer(raw[: self.buffer_size], np.uint8).reshape(
                (self.height, self.width, 4)
            )
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

        # 非 stream 模式下，minicap 输出 JPEG
        arr = np.frombuffer(raw, np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode JPEG frame from minicap")
        return image

