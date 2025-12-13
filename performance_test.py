#!/usr/bin/env python3
"""
MSC 框架性能测试脚本

对 ADB, DroidCast, MiniCap 三种截图方案进行全面的性能测试，并生成详细的测试报告。

测试指标：
- 平均延迟 (ms)
- 最小/最大延迟 (ms)
- 帧率 (FPS)
- 吞吐量 (frames/second)
- 稳定性 (标准差)
- 初始化时间
- 首帧延迟

运行方式：
    python performance_test.py
    python performance_test.py --iterations 100 --warmup 5
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
from adbutils import adb

# Import all screencap implementations
from msc.adbcap import ADBCap
from msc.adbblitz import ADBBlitz
from msc.droidcast import DroidCast
from msc.minicap import MiniCap, MiniCapUnSupportError


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    method: str  # 截图方法名称
    total_iterations: int  # 总测试次数
    warmup_iterations: int  # 预热次数

    # 延迟指标 (毫秒)
    avg_latency_ms: float  # 平均延迟
    min_latency_ms: float  # 最小延迟
    max_latency_ms: float  # 最大延迟
    median_latency_ms: float  # 中位数延迟
    std_latency_ms: float  # 延迟标准差
    p95_latency_ms: float  # 95分位延迟
    p99_latency_ms: float  # 99分位延迟

    # 吞吐量指标
    fps: float  # 帧率 (frames per second)
    total_duration_s: float  # 总耗时 (秒)

    # 初始化指标
    init_time_ms: float  # 初始化耗时
    first_frame_ms: float  # 首帧延迟

    # 图像质量
    image_width: int  # 图像宽度
    image_height: int  # 图像高度
    image_size_kb: float  # 平均图像大小 (KB)

    # 成功率
    success_rate: float  # 成功率 (0-1)
    failed_count: int  # 失败次数

    # 原始数据
    latencies_ms: List[float]  # 所有延迟数据

    def to_dict(self):
        """转换为字典"""
        d = asdict(self)
        # 移除原始延迟数据以减小输出大小
        d.pop('latencies_ms', None)
        return d


class PerformanceTester:
    """性能测试器"""

    def __init__(self, serial: str, iterations: int = 50, warmup: int = 3):
        """
        初始化性能测试器

        Args:
            serial: 设备序列号
            iterations: 测试迭代次数
            warmup: 预热次数
        """
        self.serial = serial
        self.iterations = iterations
        self.warmup = warmup
        self.device = adb.device(serial)
        self.sdk = int(self.device.getprop("ro.build.version.sdk"))

    def test_adbcap(self) -> Optional[PerformanceMetrics]:
        """测试 ADBCap 性能"""
        print(f"\n{'='*60}")
        print(f"Testing ADBCap Performance")
        print(f"{'='*60}")

        # 初始化计时
        init_start = time.time()
        try:
            cap = ADBCap(self.serial)
        except Exception as e:
            print(f"Failed to initialize ADBCap: {e}")
            return None
        init_time_ms = (time.time() - init_start) * 1000

        try:
            # 首帧计时
            first_frame_start = time.time()
            first_img = cap.screencap()
            first_frame_ms = (time.time() - first_frame_start) * 1000

            # 预热
            print(f"Warming up ({self.warmup} iterations)...")
            for _ in range(self.warmup):
                cap.screencap()

            # 正式测试
            print(f"Running performance test ({self.iterations} iterations)...")
            latencies = []
            failed = 0
            total_size = 0

            test_start = time.time()
            for i in range(self.iterations):
                try:
                    frame_start = time.time()
                    img = cap.screencap()
                    frame_end = time.time()

                    latency = (frame_end - frame_start) * 1000
                    latencies.append(latency)
                    total_size += img.nbytes

                    if (i + 1) % 10 == 0:
                        print(f"  Progress: {i+1}/{self.iterations} ({latency:.2f}ms)")
                except Exception as e:
                    print(f"  Failed at iteration {i+1}: {e}")
                    failed += 1

            total_duration = time.time() - test_start

            # 计算指标
            latencies_arr = np.array(latencies)
            metrics = PerformanceMetrics(
                method="ADBCap",
                total_iterations=self.iterations,
                warmup_iterations=self.warmup,
                avg_latency_ms=float(np.mean(latencies_arr)),
                min_latency_ms=float(np.min(latencies_arr)),
                max_latency_ms=float(np.max(latencies_arr)),
                median_latency_ms=float(np.median(latencies_arr)),
                std_latency_ms=float(np.std(latencies_arr)),
                p95_latency_ms=float(np.percentile(latencies_arr, 95)),
                p99_latency_ms=float(np.percentile(latencies_arr, 99)),
                fps=len(latencies) / total_duration,
                total_duration_s=total_duration,
                init_time_ms=init_time_ms,
                first_frame_ms=first_frame_ms,
                image_width=first_img.shape[1],
                image_height=first_img.shape[0],
                image_size_kb=total_size / len(latencies) / 1024,
                success_rate=(self.iterations - failed) / self.iterations,
                failed_count=failed,
                latencies_ms=latencies
            )

            self._print_metrics(metrics)
            return metrics

        finally:
            cap.close()

    def test_adbblitz(self) -> Optional[PerformanceMetrics]:
        """测试 ADBBlitz 性能"""
        print(f"\n{'='*60}")
        print(f"Testing ADBBlitz Performance")
        print(f"{'='*60}")

        # 初始化计时
        init_start = time.time()
        try:
            cap = ADBBlitz(self.serial)
        except Exception as e:
            print(f"Failed to initialize ADBBlitz: {e}")
            return None
        init_time_ms = (time.time() - init_start) * 1000

        try:
            # 首帧计时
            first_frame_start = time.time()
            first_img = cap.screencap()
            first_frame_ms = (time.time() - first_frame_start) * 1000

            # 预热
            print(f"Warming up ({self.warmup} iterations)...")
            for _ in range(self.warmup):
                cap.screencap()

            # 正式测试
            print(f"Running performance test ({self.iterations} iterations)...")
            latencies = []
            failed = 0
            total_size = 0

            test_start = time.time()
            for i in range(self.iterations):
                try:
                    frame_start = time.time()
                    img = cap.screencap()
                    frame_end = time.time()

                    latency = (frame_end - frame_start) * 1000
                    latencies.append(latency)
                    total_size += img.nbytes

                    if (i + 1) % 10 == 0:
                        print(f"  Progress: {i+1}/{self.iterations} ({latency:.2f}ms)")
                except Exception as e:
                    print(f"  Failed at iteration {i+1}: {e}")
                    failed += 1

            total_duration = time.time() - test_start

            # 计算指标
            latencies_arr = np.array(latencies)
            metrics = PerformanceMetrics(
                method="ADBBlitz",
                total_iterations=self.iterations,
                warmup_iterations=self.warmup,
                avg_latency_ms=float(np.mean(latencies_arr)),
                min_latency_ms=float(np.min(latencies_arr)),
                max_latency_ms=float(np.max(latencies_arr)),
                median_latency_ms=float(np.median(latencies_arr)),
                std_latency_ms=float(np.std(latencies_arr)),
                p95_latency_ms=float(np.percentile(latencies_arr, 95)),
                p99_latency_ms=float(np.percentile(latencies_arr, 99)),
                fps=len(latencies) / total_duration,
                total_duration_s=total_duration,
                init_time_ms=init_time_ms,
                first_frame_ms=first_frame_ms,
                image_width=first_img.shape[1],
                image_height=first_img.shape[0],
                image_size_kb=total_size / len(latencies) / 1024,
                success_rate=(self.iterations - failed) / self.iterations,
                failed_count=failed,
                latencies_ms=latencies
            )

            self._print_metrics(metrics)
            return metrics

        finally:
            cap.close()

    def test_droidcast(self) -> Optional[PerformanceMetrics]:
        """测试 DroidCast 性能"""
        print(f"\n{'='*60}")
        print(f"Testing DroidCast Performance")
        print(f"{'='*60}")

        # 初始化计时
        init_start = time.time()
        try:
            cap = DroidCast(self.serial)
        except Exception as e:
            print(f"Failed to initialize DroidCast: {e}")
            return None
        init_time_ms = (time.time() - init_start) * 1000

        try:
            # 首帧计时
            first_frame_start = time.time()
            first_img = cap.screencap()
            first_frame_ms = (time.time() - first_frame_start) * 1000

            # 预热
            print(f"Warming up ({self.warmup} iterations)...")
            for _ in range(self.warmup):
                cap.screencap()

            # 正式测试
            print(f"Running performance test ({self.iterations} iterations)...")
            latencies = []
            failed = 0
            total_size = 0

            test_start = time.time()
            for i in range(self.iterations):
                try:
                    frame_start = time.time()
                    img = cap.screencap()
                    frame_end = time.time()

                    latency = (frame_end - frame_start) * 1000
                    latencies.append(latency)
                    total_size += img.nbytes

                    if (i + 1) % 10 == 0:
                        print(f"  Progress: {i+1}/{self.iterations} ({latency:.2f}ms)")
                except Exception as e:
                    print(f"  Failed at iteration {i+1}: {e}")
                    failed += 1

            total_duration = time.time() - test_start

            # 计算指标
            latencies_arr = np.array(latencies)
            metrics = PerformanceMetrics(
                method="DroidCast",
                total_iterations=self.iterations,
                warmup_iterations=self.warmup,
                avg_latency_ms=float(np.mean(latencies_arr)),
                min_latency_ms=float(np.min(latencies_arr)),
                max_latency_ms=float(np.max(latencies_arr)),
                median_latency_ms=float(np.median(latencies_arr)),
                std_latency_ms=float(np.std(latencies_arr)),
                p95_latency_ms=float(np.percentile(latencies_arr, 95)),
                p99_latency_ms=float(np.percentile(latencies_arr, 99)),
                fps=len(latencies) / total_duration,
                total_duration_s=total_duration,
                init_time_ms=init_time_ms,
                first_frame_ms=first_frame_ms,
                image_width=first_img.shape[1],
                image_height=first_img.shape[0],
                image_size_kb=total_size / len(latencies) / 1024,
                success_rate=(self.iterations - failed) / self.iterations,
                failed_count=failed,
                latencies_ms=latencies
            )

            self._print_metrics(metrics)
            return metrics

        finally:
            cap.close()

    def test_minicap(self) -> Optional[PerformanceMetrics]:
        """测试 MiniCap 性能"""
        print(f"\n{'='*60}")
        print(f"Testing MiniCap Performance")
        print(f"{'='*60}")

        # 检查 SDK 版本
        if self.sdk > 34:
            print(f"MiniCap does not support Android SDK {self.sdk} (Max 34). Skipping.")
            return None

        # 初始化计时
        init_start = time.time()
        try:
            cap = MiniCap(self.serial, use_stream=True)
        except MiniCapUnSupportError as e:
            print(f"MiniCap not supported: {e}")
            return None
        except Exception as e:
            print(f"Failed to initialize MiniCap: {e}")
            return None
        init_time_ms = (time.time() - init_start) * 1000

        try:
            # 首帧计时
            first_frame_start = time.time()
            first_img = cap.screencap()
            first_frame_ms = (time.time() - first_frame_start) * 1000

            # 预热
            print(f"Warming up ({self.warmup} iterations)...")
            for _ in range(self.warmup):
                cap.screencap()

            # 正式测试
            print(f"Running performance test ({self.iterations} iterations)...")
            latencies = []
            failed = 0
            total_size = 0

            test_start = time.time()
            for i in range(self.iterations):
                try:
                    frame_start = time.time()
                    img = cap.screencap()
                    frame_end = time.time()

                    latency = (frame_end - frame_start) * 1000
                    latencies.append(latency)
                    total_size += img.nbytes

                    if (i + 1) % 10 == 0:
                        print(f"  Progress: {i+1}/{self.iterations} ({latency:.2f}ms)")
                except Exception as e:
                    print(f"  Failed at iteration {i+1}: {e}")
                    failed += 1

            total_duration = time.time() - test_start

            # 计算指标
            latencies_arr = np.array(latencies)
            metrics = PerformanceMetrics(
                method="MiniCap",
                total_iterations=self.iterations,
                warmup_iterations=self.warmup,
                avg_latency_ms=float(np.mean(latencies_arr)),
                min_latency_ms=float(np.min(latencies_arr)),
                max_latency_ms=float(np.max(latencies_arr)),
                median_latency_ms=float(np.median(latencies_arr)),
                std_latency_ms=float(np.std(latencies_arr)),
                p95_latency_ms=float(np.percentile(latencies_arr, 95)),
                p99_latency_ms=float(np.percentile(latencies_arr, 99)),
                fps=len(latencies) / total_duration,
                total_duration_s=total_duration,
                init_time_ms=init_time_ms,
                first_frame_ms=first_frame_ms,
                image_width=first_img.shape[1],
                image_height=first_img.shape[0],
                image_size_kb=total_size / len(latencies) / 1024,
                success_rate=(self.iterations - failed) / self.iterations,
                failed_count=failed,
                latencies_ms=latencies
            )

            self._print_metrics(metrics)
            return metrics

        finally:
            cap.close()

    def _print_metrics(self, metrics: PerformanceMetrics):
        """打印性能指标"""
        print(f"\n{metrics.method} Performance Results:")
        print(f"  Initialization time: {metrics.init_time_ms:.2f}ms")
        print(f"  First frame latency: {metrics.first_frame_ms:.2f}ms")
        print(f"  Average latency: {metrics.avg_latency_ms:.2f}ms")
        print(f"  Median latency: {metrics.median_latency_ms:.2f}ms")
        print(f"  Min latency: {metrics.min_latency_ms:.2f}ms")
        print(f"  Max latency: {metrics.max_latency_ms:.2f}ms")
        print(f"  Std deviation: {metrics.std_latency_ms:.2f}ms")
        print(f"  P95 latency: {metrics.p95_latency_ms:.2f}ms")
        print(f"  P99 latency: {metrics.p99_latency_ms:.2f}ms")
        print(f"  FPS: {metrics.fps:.2f}")
        print(f"  Total duration: {metrics.total_duration_s:.2f}s")
        print(f"  Image resolution: {metrics.image_width}x{metrics.image_height}")
        print(f"  Average image size: {metrics.image_size_kb:.2f}KB")
        print(f"  Success rate: {metrics.success_rate*100:.1f}%")
        if metrics.failed_count > 0:
            print(f"  Failed captures: {metrics.failed_count}")

    def run_all_tests(self) -> List[PerformanceMetrics]:
        """运行所有性能测试"""
        results = []

        # 测试 ADBCap
        adb_metrics = self.test_adbcap()
        if adb_metrics:
            results.append(adb_metrics)

        # 测试 ADBBlitz
        adbblitz_metrics = self.test_adbblitz()
        if adbblitz_metrics:
            results.append(adbblitz_metrics)

        # 测试 DroidCast
        droidcast_metrics = self.test_droidcast()
        if droidcast_metrics:
            results.append(droidcast_metrics)

        # 测试 MiniCap
        minicap_metrics = self.test_minicap()
        if minicap_metrics:
            results.append(minicap_metrics)

        return results


def generate_report(results: List[PerformanceMetrics], output_dir: Path):
    """生成性能测试报告"""
    if not results:
        print("No results to generate report")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成 JSON 报告
    json_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [m.to_dict() for m in results]
    }

    json_path = output_dir / "performance_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report saved to: {json_path}")

    # 生成 Markdown 报告
    md_path = output_dir / "performance_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# MSC 框架性能测试报告\n\n")
        f.write(f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 摘要表格
        f.write("## 性能摘要\n\n")
        f.write("| 方案 | 平均延迟 | 中位延迟 | P95延迟 | FPS | 初始化时间 | 首帧延迟 | 成功率 |\n")
        f.write("|------|----------|----------|---------|-----|------------|----------|--------|\n")

        for m in results:
            f.write(f"| {m.method} | {m.avg_latency_ms:.2f}ms | {m.median_latency_ms:.2f}ms | "
                   f"{m.p95_latency_ms:.2f}ms | {m.fps:.2f} | {m.init_time_ms:.2f}ms | "
                   f"{m.first_frame_ms:.2f}ms | {m.success_rate*100:.1f}% |\n")

        # 详细结果
        f.write("\n## 详细结果\n\n")
        for m in results:
            f.write(f"### {m.method}\n\n")
            f.write(f"**基本信息**:\n")
            f.write(f"- 测试次数: {m.total_iterations}\n")
            f.write(f"- 预热次数: {m.warmup_iterations}\n")
            f.write(f"- 图像分辨率: {m.image_width}x{m.image_height}\n")
            f.write(f"- 平均图像大小: {m.image_size_kb:.2f}KB\n\n")

            f.write(f"**延迟指标**:\n")
            f.write(f"- 平均延迟: {m.avg_latency_ms:.2f}ms\n")
            f.write(f"- 中位数延迟: {m.median_latency_ms:.2f}ms\n")
            f.write(f"- 最小延迟: {m.min_latency_ms:.2f}ms\n")
            f.write(f"- 最大延迟: {m.max_latency_ms:.2f}ms\n")
            f.write(f"- 标准差: {m.std_latency_ms:.2f}ms\n")
            f.write(f"- P95延迟: {m.p95_latency_ms:.2f}ms\n")
            f.write(f"- P99延迟: {m.p99_latency_ms:.2f}ms\n\n")

            f.write(f"**吞吐量指标**:\n")
            f.write(f"- FPS: {m.fps:.2f}\n")
            f.write(f"- 总耗时: {m.total_duration_s:.2f}s\n\n")

            f.write(f"**启动指标**:\n")
            f.write(f"- 初始化时间: {m.init_time_ms:.2f}ms\n")
            f.write(f"- 首帧延迟: {m.first_frame_ms:.2f}ms\n\n")

            f.write(f"**可靠性**:\n")
            f.write(f"- 成功率: {m.success_rate*100:.1f}%\n")
            f.write(f"- 失败次数: {m.failed_count}\n\n")

        # 性能对比
        f.write("## 性能对比分析\n\n")
        if len(results) > 1:
            # 找出最快的方案
            fastest = min(results, key=lambda x: x.avg_latency_ms)
            f.write(f"**延迟最低**: {fastest.method} ({fastest.avg_latency_ms:.2f}ms)\n\n")

            # 找出 FPS 最高的方案
            highest_fps = max(results, key=lambda x: x.fps)
            f.write(f"**FPS最高**: {highest_fps.method} ({highest_fps.fps:.2f} fps)\n\n")

            # 找出最稳定的方案
            most_stable = min(results, key=lambda x: x.std_latency_ms)
            f.write(f"**最稳定**: {most_stable.method} (标准差 {most_stable.std_latency_ms:.2f}ms)\n\n")

            # 找出初始化最快的方案
            fastest_init = min(results, key=lambda x: x.init_time_ms)
            f.write(f"**初始化最快**: {fastest_init.method} ({fastest_init.init_time_ms:.2f}ms)\n\n")

    print(f"Markdown report saved to: {md_path}")

    # 生成延迟分布数据（用于可视化）
    distribution_data = {}
    for m in results:
        distribution_data[m.method] = {
            "latencies": m.latencies_ms,
            "avg": m.avg_latency_ms,
            "median": m.median_latency_ms,
            "p95": m.p95_latency_ms,
            "p99": m.p99_latency_ms
        }

    dist_path = output_dir / "latency_distribution.json"
    with open(dist_path, "w", encoding="utf-8") as f:
        json.dump(distribution_data, f, indent=2)
    print(f"Latency distribution data saved to: {dist_path}")


def main():
    parser = argparse.ArgumentParser(
        description="MSC 框架性能测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--serial", "-s",
        help="设备序列号 (默认使用第一个设备)"
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=50,
        help="测试迭代次数 (默认: 50)"
    )
    parser.add_argument(
        "--warmup", "-w",
        type=int,
        default=3,
        help="预热次数 (默认: 3)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="performance_results",
        help="输出目录 (默认: performance_results)"
    )

    args = parser.parse_args()

    # 获取设备
    if args.serial:
        serial = args.serial
    else:
        devices = adb.device_list()
        if not devices:
            print("Error: No Android devices connected.")
            print("Please connect a device and try again.")
            return 1
        serial = devices[0].serial

    device = adb.device(serial)
    print(f"Using device: {serial}")
    print(f"Device model: {device.getprop('ro.product.model')}")
    print(f"Android SDK: {device.getprop('ro.build.version.sdk')}")
    print(f"Test iterations: {args.iterations}")
    print(f"Warmup iterations: {args.warmup}")

    # 运行测试
    tester = PerformanceTester(serial, args.iterations, args.warmup)
    results = tester.run_all_tests()

    # 生成报告
    output_dir = Path(args.output)
    generate_report(results, output_dir)

    # 打印总结
    print(f"\n{'='*60}")
    print("Performance Testing Completed")
    print(f"{'='*60}")
    print(f"Total methods tested: {len(results)}")
    print(f"Reports saved to: {output_dir.absolute()}")

    return 0


if __name__ == "__main__":
    exit(main())
