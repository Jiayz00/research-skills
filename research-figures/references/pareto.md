# 取舍与 Pareto 前沿

**回答：** 为了得到收益，你付出了什么——reward vs KL 散度、accuracy vs 延迟、质量 vs 参数量或成本。

当方法有一个"沿曲线移动"的旋钮、而不是停在单点上时用这张图。只报每个方法的一个工作点，等于把一次旋钮选择包装成结论：换一个 β，排名就翻转。前沿才是诚实的对象，也是这张图本身。

## 前沿是主张；各次运行是证据

把所有运行画成淡色散点，再把每个方法的非支配点连成实线（样式模块的 `pareto_front`）。读者要做的比较是"一个方法的前沿是否在整个范围内位于另一个的左上方"，而不是"一个点是否赢另一个点"。

把被支配的运行藏起来，图会干净，但会更差：散点正是显示"方法不稳定"或"一半设置是浪费"的东西。

**前沿线是示意，不是插值。** 两个设置之间的点你没有测量过；对离散旋钮而言它们可能根本不可达。有意义时在 caption 里说明这一点。

## 让"好的角落"显而易见

两个轴一个越低越好、一个越高越好，是读者经常读错的图。在两个轴标签里写明方向——"KL divergence (lower is better)"——永远有效且零成本。

在"好的角落"画一个小 "better ↖" 箭头读得更快，但只适用于数据没占住那个角落时；而这类图的意义通常正是"你的方法到达了好角落"——所以往往不适用。落笔前先看渲染结果。

绘图区拥挤时更好的做法：给好/坏区域加底色，而不是给区域里的点加标签——`ax.axhspan`/`axvspan`，或数据背后极低 alpha 的斜向渐变。背景承载方向、不与任何标记抢空间，也不会撞到任何东西。

成本类轴——FLOPs、延迟、参数量、token——通常用 log；线性成本轴会挤掉低成本端，而好取舍恰恰在那里。

## sweep 预算本身是结果的一部分

扫过 12 个设置的方法，前沿看起来会比扫 3 个的好——它只是有更多机会成为非支配点。在 legend 或 caption 里写明每个方法的设置数，并给每个方法可比的预算。这是取舍图"在没人撒谎的情况下美化作者方法"的最常见方式。

## 编码

- **形状编码方法、色相也编码方法**——故意冗余，让图在灰度打印和色 blind 读者那里都活着。
- **只有当旋钮设置本身的效应就是故事时**（"β 控制策略漂移多远"）才改按设置着色。代价是每个值一个图例项，超过约六个就变成没人看的查表——直接把承载论证的两三个设置标在图上，其余不进图例。
- **形状编码方法、深浅编码有序旋钮**是很好的搭配：marker 区分方法，单色相浅到深（`family()`）在每个方法内排序设置。两个变量用两个通道，读起来干净。不成立的是三通道——形状、色相、再加一个 colorbar 只编两个变量。

## 陷阱

| 陷阱 | 修法 |
| --- | --- |
| 按 sweep 顺序连点 | 连前沿，不连运行序 |
| 只画前沿 | 被支配的运行淡色展示；散布本身是结果 |
| sweep 预算不等且不说明 | 写明每个方法的 n；预算对齐 |
| 两个轴都没说哪边更好 | 好角落加箭头，或写进标签 |
| 跨数量级的成本用线性轴 | 成本轴取 log |
| 每个超参值一个图例项 | 只直接标注重要的几个 |
| 先折种子均值再取前沿 | 前沿按设置取，设置内展示种子散布 |

## 模板

`figs/pareto.py`，读取 `figs/pareto.csv`（`method,setting,seed,kl,reward`）：

```python
"""Reward against KL divergence. Regenerate: python figs/pareto.py"""

import csv
from collections import defaultdict

import numpy as np
from figstyle import PALETTE, TEXT, figure, pareto_front, save, use_style

DATA = "figs/pareto.csv"

# Shape and hue both carry the method: redundant so the figure survives
# greyscale and a colorblind reader.
METHODS = {"GRPO": ("blue", "o"), "ES": ("red", "D")}


def load(path):
    runs = defaultdict(lambda: ([], [], set()))
    with open(path) as handle:
        for row in csv.DictReader(handle):
            kl, reward, settings = runs[row["method"]]
            kl.append(float(row["kl"]))
            reward.append(float(row["reward"]))
            settings.add(row["setting"])
    return {
        method: (np.array(kl), np.array(reward), len(settings))
        for method, (kl, reward, settings) in runs.items()
    }


def main():
    use_style()
    runs = load(DATA)

    fig, ax = figure(width=TEXT, ratio=0.62)
    for method, (color_name, marker) in METHODS.items():
        kl, reward, n_settings = runs[method]
        color = PALETTE[color_name]
        # Every run, faded: the spread is part of the result.
        ax.scatter(kl, reward, marker=marker, s=16, color=color, alpha=0.35, linewidth=0)
        front = pareto_front(kl, reward, minimize_x=True, maximize_y=True)
        ax.plot(
            kl[front], reward[front],
            marker=marker, markersize=4, color=color, linewidth=1.1, zorder=3,
            label=f"{method} ({n_settings} settings)",
        )

    ax.set_xlabel("KL divergence from the base model (lower is better)")
    ax.set_ylabel("Reward (higher is better)")
    ax.grid(True, axis="both")
    ax.legend(loc="lower right", frameon=True, framealpha=1.0, edgecolor="black")

    save(fig, "figs/pareto")


if __name__ == "__main__":
    main()
```

## 检查清单

- [ ] 被支配的运行淡色可见；前沿只连非支配点。
- [ ] 写明每个方法的设置数，预算可比。
- [ ] 两个轴标签都说明哪边更好。
- [ ] 跨数量级的成本轴取 log。
- [ ] 形状与色相都编码方法；没有第三种编码。
- [ ] caption 说明前沿线是示意、不是实测插值。
