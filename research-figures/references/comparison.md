# Benchmark 对比与消融

**回答：** 哪个方法赢——跨一组 benchmark，或跨你消融掉的组件。

两个看起来像、但要不同图的问题：

| 比较是 | 用 | 因为 |
| --- | --- | --- |
| 多个方法 × 多个 benchmark，分数从 0 起算 | **分组柱状图**——评测论文的头图 | 轴从 0 起时，长度是诚实的编码；分组让读者能沿一个方法扫过所有 benchmark |
| 单一指标，差异相对种子噪声很小 | **差值点须图（dot-and-whisker）** | 位置编码数值，轴可以只覆盖关心的范围而不撒谎 |

两条规则之下的一条：**柱子的长度是对"轴从 0 开始"的承诺。** 截断柱状轴来让 0.4 分的差距显得决定性，是 ML 里最常见的不诚实图。这是在反对截断，不是反对柱子——accuracy、pass@k、win rate、计数都天然从 0 起，柱子对它们是正确选择。

## 跨 benchmark 的分组柱

**色相 = 方法族，深浅 = 变体。** 未调优的基座模型用灰，先前工作一个色相，你的方法一个色相，族内由浅到深（样式模块的 `family()`）。读者在读图例之前就能分清"他们"和"我们"。七种任意颜色什么也传达不了。

**每个分组里的方法顺序完全一致**，并与图例顺序一致。这张图是沿一个方法的柱位扫过各分组来读的；按分组重新排序会毁掉这一点。

**每根柱子标数值。** 这让图同时干结果表的活，引用数字的读者不用眯眼看轴。这是唯一允许文字低于 7pt 刻度、一直到 5pt 下限的地方：标签与柱高冗余，读不清标签的读者仍能从轴恢复数值。全文宽度下约 5pt；如果柱子密到标签相撞，那是在提示你减方法或拆图，而不是继续缩字号。

**有意识地排列 benchmark 分组的顺序**——按难度、规模，或与结果表一致。字母序是浪费机会。

**图例压在绘图区上时要加框**，放在柱子最矮处。本风格默认图例无框——放在坐标轴外时正确；浮在数据上时必须有不透明底，否则会被读成图的一部分。

分组柱图的上限约 6 方法 × 6 分组。再往上，怎么调样式都救不回来——用表格。

## 消融：画差值

当主张是"这个组件重要"时，画 `变体 − 基线`，在 0 处画线，按效应大小排序。读者看到符号、大小，以及区间是否跨过 0——这就是全部问题。

画**差值本身的区间**（`diff_ci`）。两个各自变体的区间重叠**并不**意味着差值与 0 不可区分——这是一个被广泛重复的错误。如果某个变体的区间跨过 0，诚实读数就是"在这个种子数下检测不到效应"。

每个变体只有一个种子时没有区间：在 caption 里写 "single seed"，不要画暗示相反信息的须线。

## 什么时候该用表格

读者需要精确数字、变体超过 ~8 个、或差异在噪声之内时，`booktabs` 表格比任何图都传达得好。表格排版见 `research-paper` 技能。

## 陷阱

| 陷阱 | 修法 |
| --- | --- |
| 柱状图截断 y 轴 | 从 0 起，或改用差值点图 |
| 每个方法一种色相 | 灰基座，每族一个色相，族内深浅 |
| 方法顺序逐组变化 | 固定顺序；与图例一致 |
| 误差棒含义不明 | 写明："95% CI over 5 seeds"。SD、SEM、CI 相差数倍 |
| 45° 旋转的刻度标签 | 水平点图 + 左对齐名称，或加宽图 |
| "我们"永远排第一 | 诚实排序；在某些子集上输也是结果 |
| 柱标签相撞 | 减少方法或拆图——不是缩小字号 |

## 模板 —— 分组 benchmark 柱

`figs/benchmarks.py`，读取 `figs/benchmarks.csv`（`benchmark,method,score`）：

```python
"""Accuracy across benchmarks. Regenerate: python figs/benchmarks.py"""

import csv
import math
from collections import defaultdict

import numpy as np
from figstyle import MUTED, WIDE, family, figure, save, use_style

DATA = "figs/benchmarks.csv"

# Fixed order everywhere, and the family each method belongs to. Grey for the
# untuned model, blue for prior work, red for ours.
METHODS = [
    ("Qwen2.5-Math-7B", "base"),
    ("SimpleRL-Zero-7B (GRPO)", "prior"),
    ("OpenReasoner-Zero-7B (PPO)", "prior"),
    ("Oat-Zero-7B (Dr.GRPO)", "prior"),
    (r"ES$_\mathrm{CHKPT-1}$", "ours"),
    (r"ES$_\mathrm{CHKPT-2}$", "ours"),
    (r"ES$_\mathrm{CHKPT-3}$", "ours"),
]
BENCHMARKS = ["AIME 2024", "Minerva Math", "OlympiadBench", "AMC", "MATH500"]


def method_colors():
    members = defaultdict(list)
    for name, group in METHODS:
        members[group].append(name)
    shades = {
        "base": [MUTED] * len(members["base"]),
        "prior": family("blue", len(members["prior"])),
        "ours": family("red", len(members["ours"])),
    }
    return {
        name: shades[group][members[group].index(name)] for name, group in METHODS
    }


def load(path):
    scores = defaultdict(dict)
    with open(path) as handle:
        for row in csv.DictReader(handle):
            scores[row["method"]][row["benchmark"]] = float(row["score"])
    return scores


def main():
    use_style()
    scores = load(DATA)
    colors = method_colors()

    fig, ax = figure(width=WIDE, ratio=0.28)
    x = np.arange(len(BENCHMARKS))
    # Near-touching bars inside a group; the gap between groups does the separating.
    width = 0.9 / len(METHODS)

    for i, (name, _) in enumerate(METHODS):
        offset = (i - (len(METHODS) - 1) / 2) * width
        bars = ax.bar(
            x + offset,
            [scores[name][benchmark] for benchmark in BENCHMARKS],
            width,
            label=name,
            color=colors[name],
            edgecolor="black",
            linewidth=0.4,
        )
        # Redundant with the bar height, so it may sit at the 5pt floor.
        ax.bar_label(bars, fmt="%.1f", fontsize=5, padding=1.5)

    ax.set_xticks(x, BENCHMARKS)
    ax.set_ylabel("Accuracy (%)")
    # Derived, never hardcoded: a bar clipped at the axes edge no longer
    # encodes its value, which is the failure this whole reference is about.
    highest = max(v for row in scores.values() for v in row.values())
    top = max(10, 10 * math.ceil(highest * 1.12 / 10))
    ax.set_ylim(0, top)
    ax.set_yticks(range(0, top + 1, 10))
    ax.tick_params(axis="x", length=0)
    ax.legend(
        ncol=2, loc="upper left", fontsize=6.5,
        frameon=True, framealpha=1.0, edgecolor="black", borderpad=0.5,
    )

    save(fig, "figs/benchmarks")


if __name__ == "__main__":
    main()
```

## 模板 —— 消融差值

`figs/ablation.py`，读取 `figs/ablation.csv`（`variant,seed,value`）：

```python
"""Accuracy change vs. the baseline. Regenerate: python figs/ablation.py"""

import csv
from collections import defaultdict

import numpy as np
from figstyle import BASELINE, COLUMN, PALETTE, diff_ci, figure, save, use_style

DATA = "figs/ablation.csv"
REFERENCE = "baseline"
HIGHLIGHT = "ours"


def load(path):
    runs = defaultdict(list)
    with open(path) as handle:
        for row in csv.DictReader(handle):
            runs[row["variant"]].append(float(row["value"]))
    return {variant: np.array(values) for variant, values in runs.items()}


def main():
    use_style()
    runs = load(DATA)
    reference = runs[REFERENCE]
    n_seeds = min(len(values) for values in runs.values())

    effects = [
        (variant, *diff_ci(values, reference))
        for variant, values in runs.items()
        if variant != REFERENCE
    ]
    effects.sort(key=lambda row: row[1])  # ascending: best ends up on top

    fig, ax = figure(width=COLUMN, ratio=0.1 + 0.16 * len(effects))
    ax.axvline(0, color=BASELINE, linewidth=0.8, zorder=1)

    for y, (variant, delta, lo, hi) in enumerate(effects):
        color = PALETTE["blue"] if variant == HIGHLIGHT else "#4D4D4D"
        ax.plot([lo, hi], [y, y], color=color, linewidth=1.0, solid_capstyle="round", zorder=2)
        ax.plot([delta], [y], "o", color=color, zorder=3)
        # Sign included: a delta figure is read for direction first.
        ax.annotate(
            f"{delta:+.2f}",
            xy=(hi, y), xytext=(4, 0), textcoords="offset points",
            va="center", fontsize=7, color=color,
        )

    ax.set_yticks(range(len(effects)), [variant for variant, *_ in effects])
    ax.set_ylim(-0.6, len(effects) - 0.4)
    ax.set_xlabel(f"Accuracy vs. {REFERENCE} (points)")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.margins(x=0.18)
    print(f"n={n_seeds} seeds per variant — state this in the caption")

    save(fig, "figs/ablation")


if __name__ == "__main__":
    main()
```

## 检查清单

- [ ] 柱子从 0 起；没有任何截断。
- [ ] 色相=方法族，深浅=变体；基座模型用灰。
- [ ] 方法顺序跨分组一致，且与图例一致。
- [ ] 每根柱子都有标签，且标签不相撞。
- [ ] 差值图：区间是**差值的**区间，n 与含义写进 caption。
- [ ] 图例只在压着数据时加框，并避开最高的柱子。
- [ ] 变体超过 ~8 个、或需要精确数字？改用表格。
