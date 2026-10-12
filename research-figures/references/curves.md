# 学习与训练曲线

**回答：** 指标随训练怎么变；两条曲线之间的差距是否大于种子噪声。

这是投稿论文里最常画错的图——它误导人的地方画完后看不见：错的 x 轴，和单一种子。

## 先定 x 轴

x 轴决定比较的含义。只有当每次迭代的工作量相同时，优化 **step** 才是公平的轴。一旦曲线之间 batch size、序列长度、模型大小或硬件不同，step 就不可比，必须改画真正有差异的量：

| 比较对象 | x 轴画什么 |
| --- | --- |
| 同配置、不同种子或代码改动 | 优化 step |
| 不同 batch size 或序列长度 | 已见 token（或样本）数 |
| 不同模型大小 | FLOPs，或 token 数并逐条标注规模 |
| 速度/效率主张 | 墙钟时间，并写明硬件 |

"用一半 step 收敛"但每步耗时两倍的方法并不更快——step 轴的图恰好把这一点藏起来。

## 聚合种子，绝不挑一个

至少 3 个种子，效果小时用 5 个。线画均值，同色低 alpha 的带画 95% 区间（样式模块的 `band()`）。caption 里写明 n。

- ±1 标准差的带回答的是"种子间有多散"，不是"均值估得多准"——用区间。
- 种子出现定性分歧（一个发散、其他没有）——那本身就是结果。把各次运行画成细线，不要用宽 band 掩盖分歧。
- 种子很少落在相同的 step 网格上：先插值到公共网格再平均；直接平均参差数组会悄悄截到最短的那条。

## 平滑是对数据的主张

训练 loss 有噪声，不平滑可能没法读；但平滑是对证据的变换：

- 平滑方式必须写进 caption（"EMA, α=0.1"）。
- 平滑线下画一条淡淡的原始曲线。只给平滑线会让读者以为运行真有那么稳。
- 稀疏的评测指标绝不平滑——那是在真实测量之间编造数据点。

## 陷阱

| 陷阱 | 修法 |
| --- | --- |
| 截断 y 轴，让小差距显得决定性 | 覆盖真正重要的范围；放大时要说明 |
| 用了 log 轴却不说 | 在标签上写明。指标跨一个数量级以上、或主张本身关于比例时才用 log-y；从 4.7 到 1.6 的有界 loss 线性读起来更好 |
| 图例挡住关心的区域 | 在曲线右端直接标注（`label_ends`）；图例只是查表 |
| 一个面板塞太多曲线 | 只留主张需要的 4 条；其余进附录表格 |
| 基线用了调色板颜色 | 基线与随机水平用灰色（`BASELINE`）——颜色留给被比较的对象 |
| 曲线在 x 方向长度不一致却不说明 | 说明某条为何提前停（发散、预算用尽） |

## 模板

`figs/loss_curve.py`，读取从运行日志提取的 tidy CSV（`variant,seed,step,value`）：

```python
"""Validation loss over training. Regenerate: python figs/loss_curve.py"""

import csv
from collections import defaultdict

import numpy as np
from figstyle import BASELINE, COLUMN, band, figure, label_ends, save, si_ticks, use_style

DATA = "figs/loss_curve.csv"


def load(path):
    """-> {variant: (steps, runs)} with runs shaped (n_seeds, n_steps)."""
    raw = defaultdict(lambda: defaultdict(list))
    with open(path) as handle:
        for row in csv.DictReader(handle):
            raw[row["variant"]][row["seed"]].append((float(row["step"]), float(row["value"])))

    series = {}
    for variant, seeds in raw.items():
        curves = [sorted(points) for points in seeds.values()]
        grid = np.array([step for step, _ in curves[0]])
        # Seeds log on slightly different grids, so interpolate before
        # averaging — but only across the range every seed actually reached.
        # np.interp clamps outside its input, which would invent a flat tail
        # for a run that stopped early and narrow the band around it.
        first = max(curve[0][0] for curve in curves)
        last = min(curve[-1][0] for curve in curves)
        if first > last:
            raise ValueError(f"{variant}: seeds cover no common range of steps")
        grid = grid[(grid >= first) & (grid <= last)]
        runs = np.stack([
            np.interp(grid, [s for s, _ in curve], [v for _, v in curve]) for curve in curves
        ])
        series[variant] = (grid, runs)
    return series


def main():
    use_style()
    series = load(DATA)

    fig, ax = figure(width=COLUMN, ratio=0.72)
    lines, labels = [], []
    for variant, (steps, runs) in series.items():
        color = BASELINE if variant == "baseline" else None
        lines.append(band(ax, steps, runs, color=color))
        labels.append(f"{variant} (n={runs.shape[0]})")

    ax.set_xlabel("Tokens seen")
    ax.set_ylabel("Validation loss")
    label_ends(ax, lines, labels)
    si_ticks(ax, "x")  # after label_ends, which moves the right limit

    save(fig, "figs/loss_curve")


if __name__ == "__main__":
    main()
```

## 检查清单

- [ ] x 轴对被比较的运行是公平的，且带单位。
- [ ] ≥3 个种子的均值 + 95% 带，n 写进 caption。
- [ ] 平滑方式写进 caption，且原始曲线可见。
- [ ] 基线是灰色；有颜色的曲线最多 4 条。
- [ ] y 范围诚实，或明确声明了放大。
