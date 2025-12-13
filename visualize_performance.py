#!/usr/bin/env python3
"""
性能测试结果可视化工具

读取 performance_report.json 并生成可视化图表。

运行方式：
    python visualize_performance.py
    python visualize_performance.py --input performance_results/performance_report.json
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_results(json_path: Path) -> dict:
    """加载性能测试结果"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_latency_comparison(results: list, output_dir: Path):
    """绘制延迟对比图"""
    methods = [r["method"] for r in results]
    avg_latencies = [r["avg_latency_ms"] for r in results]
    median_latencies = [r["median_latency_ms"] for r in results]
    p95_latencies = [r["p95_latency_ms"] for r in results]

    x = np.arange(len(methods))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar(x - width, avg_latencies, width, label='Average', color='#3498db')
    bars2 = ax.bar(x, median_latencies, width, label='Median', color='#2ecc71')
    bars3 = ax.bar(x + width, p95_latencies, width, label='P95', color='#e74c3c')

    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Screencap Latency Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # 添加数值标签
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom',
                       fontsize=9)

    autolabel(bars1)
    autolabel(bars2)
    autolabel(bars3)

    plt.tight_layout()
    output_path = output_dir / "latency_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved latency comparison chart to: {output_path}")
    plt.close()


def plot_fps_comparison(results: list, output_dir: Path):
    """绘制 FPS 对比图"""
    methods = [r["method"] for r in results]
    fps_values = [r["fps"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(methods, fps_values, color=['#3498db', '#2ecc71', '#e74c3c'])

    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('FPS (frames per second)', fontsize=12, fontweight='bold')
    ax.set_title('Screencap FPS Comparison', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),
                   textcoords="offset points",
                   ha='center', va='bottom',
                   fontsize=10,
                   fontweight='bold')

    plt.tight_layout()
    output_path = output_dir / "fps_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved FPS comparison chart to: {output_path}")
    plt.close()


def plot_initialization_comparison(results: list, output_dir: Path):
    """绘制初始化时间对比图"""
    methods = [r["method"] for r in results]
    init_times = [r["init_time_ms"] for r in results]
    first_frame_times = [r["first_frame_ms"] for r in results]

    x = np.arange(len(methods))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, init_times, width, label='Initialization', color='#9b59b6')
    bars2 = ax.bar(x + width/2, first_frame_times, width, label='First Frame', color='#f39c12')

    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Time (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Initialization and First Frame Latency', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # 添加数值标签
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom',
                       fontsize=9)

    autolabel(bars1)
    autolabel(bars2)

    plt.tight_layout()
    output_path = output_dir / "initialization_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved initialization comparison chart to: {output_path}")
    plt.close()


def plot_latency_distribution(dist_data: dict, output_dir: Path):
    """绘制延迟分布箱线图"""
    methods = list(dist_data.keys())
    latencies_data = [dist_data[m]["latencies"] for m in methods]

    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(latencies_data, labels=methods, patch_artist=True)

    # 设置颜色
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Latency Distribution (Box Plot)', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    output_path = output_dir / "latency_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved latency distribution chart to: {output_path}")
    plt.close()


def plot_stability_comparison(results: list, output_dir: Path):
    """绘制稳定性对比图（标准差）"""
    methods = [r["method"] for r in results]
    std_values = [r["std_latency_ms"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(methods, std_values, color=['#3498db', '#2ecc71', '#e74c3c'])

    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Standard Deviation (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Latency Stability Comparison (Lower is Better)', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),
                   textcoords="offset points",
                   ha='center', va='bottom',
                   fontsize=10,
                   fontweight='bold')

    plt.tight_layout()
    output_path = output_dir / "stability_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved stability comparison chart to: {output_path}")
    plt.close()


def plot_performance_radar(results: list, output_dir: Path):
    """绘制性能雷达图（多维度对比）"""
    from math import pi

    # 标准化数据（反转延迟相关指标，使得"越大越好"）
    metrics = []
    for r in results:
        # 将延迟转换为"性能"（越小越好 -> 越大越好）
        latency_score = 1000 / max(r["avg_latency_ms"], 0.01)  # 避免除零
        fps_score = r["fps"]
        stability_score = 1000 / max(r["std_latency_ms"], 0.01)  # 稳定性：标准差越小越好
        init_score = 10000 / max(r["init_time_ms"], 1)  # 初始化越快越好

        # 归一化到 0-100
        metrics.append({
            "method": r["method"],
            "latency": min(latency_score / 10, 100),
            "fps": min(fps_score / 100, 100),
            "stability": min(stability_score / 10, 100),
            "init": min(init_score / 10, 100)
        })

    categories = ['Latency\nPerformance', 'FPS', 'Stability', 'Initialization\nSpeed']
    N = len(categories)

    # 计算角度
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

    colors = ['#3498db', '#2ecc71', '#e74c3c']
    for i, m in enumerate(metrics):
        values = [m["latency"], m["fps"], m["stability"], m["init"]]
        values += values[:1]

        ax.plot(angles, values, 'o-', linewidth=2, label=m["method"], color=colors[i])
        ax.fill(angles, values, alpha=0.25, color=colors[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
    ax.grid(True)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.set_title('Performance Multi-Dimensional Comparison\n(Higher is Better)',
                 fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    output_path = output_dir / "performance_radar.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved performance radar chart to: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="可视化性能测试结果")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="performance_results/performance_report.json",
        help="性能测试 JSON 报告路径"
    )
    parser.add_argument(
        "--dist", "-d",
        type=str,
        default="performance_results/latency_distribution.json",
        help="延迟分布数据路径"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="performance_results",
        help="输出目录"
    )

    args = parser.parse_args()

    # 加载数据
    json_path = Path(args.input)
    dist_path = Path(args.dist)
    output_dir = Path(args.output)

    if not json_path.exists():
        print(f"Error: {json_path} does not exist")
        return 1

    print(f"Loading performance results from: {json_path}")
    data = load_results(json_path)
    results = data["results"]

    print(f"Generating visualization charts...")

    # 生成各种图表
    plot_latency_comparison(results, output_dir)
    plot_fps_comparison(results, output_dir)
    plot_initialization_comparison(results, output_dir)
    plot_stability_comparison(results, output_dir)
    plot_performance_radar(results, output_dir)

    # 如果有延迟分布数据，也生成分布图
    if dist_path.exists():
        with open(dist_path, "r", encoding="utf-8") as f:
            dist_data = json.load(f)
        plot_latency_distribution(dist_data, output_dir)

    print(f"\n{'='*60}")
    print("Visualization completed!")
    print(f"{'='*60}")
    print(f"All charts saved to: {output_dir.absolute()}")

    return 0


if __name__ == "__main__":
    exit(main())
