# 热图、sweep 与混淆矩阵

**回答：** 一个二维测量网格长什么样——超参 sweep、混淆矩阵、相关结构、逐层诊断。

热图用颜色编码数值，而颜色是读者精度最低的通道。它换来"一眼看见整片网格的模式"，代价是"无法精确比较相邻格子"。只有当网格的**形状本身就是发现**时才用它。

## 先确认热图是对的图

3×4 的网格不是热图；那是四条各三个点的线，线图能让读者从轴上读数值，而不是读色带。大约 5×5 起，或两个轴真正对称时（任意大小的混淆矩阵、相关矩阵）再用热图。

## colormap 是决定，不是默认值

| 数据是 | 用 | 因为 |
| --- | --- | --- |
| 有天然低端的量（loss、accuracy、计数） | `viridis`（`SEQUENTIAL`） | 感知均匀：等色步=等值步；灰度下也能读 |
| 带符号的差值、相关、相对基线的 delta | `RdBu_r`（`DIVERGING`），范围关于 0 对称 | 中点颜色必须落在 0 上，否则符号不可读 |
| 任何情况 | 绝不用 `jet`、`rainbow`、`hsv` | 它们在任意数值处有亮带，编造数据里没有的边缘 |

发散色图要自己设范围：`vmin=-max|x|`、`vmax=+max|x|`。让 matplotlib 自动缩放会把中性色放在数据中位点——那不是 0——图于是声称了并不存在的符号变化。

## colorbar 是一根轴

像标注 x 轴一样，标出它代表的量和单位。没有标签的 colorbar = 没有标签的轴。让它与图等高；多个面板同尺度时共用一个 colorbar，不要一人一个——分开的 colorbar 会邀请读者比较并不在同一尺度上的面板。

## 混淆矩阵

- **归一化，并说明怎么归的。** 类别不平衡时原始计数会让最大类看起来就是模型的全部行为。按行归一 = 每个真实类的 recall；按列归一 = precision。在 caption 里写明用的是哪种。
- **格子里标数值。** 约 12×12 以内数字放得下；再大就撤掉标注，交给 colorbar。
- **类别顺序要有意义**——按频率、按语义分组，或与你要对比的另一张矩阵完全一致。字母序会打散常常正是发现的块结构。
- **保持正方形**（`aspect="equal"`）；被拉伸的混淆矩阵读起来像类别有不同的重要性。

## 陷阱

| 陷阱 | 修法 |
| --- | --- |
| 格子之间被平滑 | `interpolation="nearest"`——热图不是图像 |
| sweep 轴标成 `0,1,2` | 标真实取值；对数间隔的轴注明 log |
| 深色格子上标注看不见 | 按格子亮度选文字颜色（`annotate_matrix`） |
| 最优格子留给读者找 | 圈出来或标记 |
| NaN 被渲染成最低色 | 给失败运行显式颜色，并说明含义 |
| 两个面板两条自动缩放的 colorbar | 一套共享归一化 + 一个 colorbar |

## 模板 —— 超参 sweep

`figs/sweep.py`，读取 `figs/sweep.csv`（`lr,batch_size,loss`）：

```python
"""Final loss over the lr x batch-size sweep. Regenerate: python figs/sweep.py"""

import csv

import matplotlib as mpl
import numpy as np
from matplotlib.patches import Rectangle
from figstyle import COLUMN, MUTED, SEQUENTIAL, annotate_matrix, figure, save, use_style

DATA = "figs/sweep.csv"


def load(path):
    with open(path) as handle:
        rows = list(csv.DictReader(handle))
    lrs = sorted({float(row["lr"]) for row in rows}, reverse=True)
    batches = sorted({int(row["batch_size"]) for row in rows})
    grid = np.full((len(lrs), len(batches)), np.nan)
    for row in rows:
        loss = row["loss"].strip()
        # A run with no loss diverged or never finished; NaN keeps it out of
        # the color scale instead of pinning it to the worst value.
        grid[lrs.index(float(row["lr"])), batches.index(int(row["batch_size"]))] = (
            float(loss) if loss else np.nan
        )
    return lrs, batches, grid


def main():
    use_style()
    lrs, batches, grid = load(DATA)

    # A diverged or OOM run is not "the worst loss"; it is a different outcome.
    cmap = mpl.colormaps[SEQUENTIAL].with_extremes(bad=MUTED)

    fig, ax = figure(width=COLUMN, ratio=0.85)
    image = ax.imshow(grid, cmap=cmap, interpolation="nearest", aspect="auto")
    annotate_matrix(ax, grid, fmt="{:.3f}")

    if np.isnan(grid).all():
        raise ValueError("every cell is empty: nothing to plot")
    row, col = np.unravel_index(np.nanargmin(grid), grid.shape)
    ax.add_patch(
        Rectangle((col - 0.5, row - 0.5), 1, 1, fill=False, edgecolor="white", linewidth=1.4)
    )

    ax.set_xticks(range(len(batches)), [str(b) for b in batches])
    ax.set_yticks(range(len(lrs)), [f"{lr:.1e}" for lr in lrs])
    ax.set_xlabel("Batch size")
    ax.set_ylabel("Learning rate")
    ax.grid(visible=False)
    fig.colorbar(image, ax=ax, label="Final validation loss", fraction=0.046, pad=0.03)

    save(fig, "figs/sweep")


if __name__ == "__main__":
    main()
```

## 模板 —— 混淆矩阵

同一套样式模块，按行归一、正方形：

```python
import matplotlib as mpl
import numpy as np
from figstyle import COLUMN, MUTED, SEQUENTIAL, annotate_matrix, figure, save, use_style

counts = np.load("figs/confusion.npy")  # (n_classes, n_classes), true x predicted
classes = ["ent", "neut", "contra"]

use_style()
support = counts.sum(axis=1, keepdims=True)
# A class with no examples is undefined, not zero recall.
recall = np.divide(counts, support, out=np.full(counts.shape, np.nan), where=support > 0)

fig, ax = figure(width=COLUMN, ratio=0.95)
cmap = mpl.colormaps[SEQUENTIAL].with_extremes(bad=MUTED)
image = ax.imshow(recall, cmap=cmap, vmin=0, vmax=1, interpolation="nearest", aspect="equal")
annotate_matrix(ax, recall, fmt="{:.2f}")
ax.set_xticks(range(len(classes)), classes)
ax.set_yticks(range(len(classes)), classes)
ax.set_xlabel("Predicted")
ax.set_ylabel("True")
ax.grid(visible=False)
fig.colorbar(image, ax=ax, label="Fraction of true class", fraction=0.046, pad=0.03)
save(fig, "figs/confusion")
```

caption 里写明是按行归一，并给出每个类的样本数——三个样本上的 1.00 和三千个样本上的 1.00 不是同一个结果。

## 检查清单

- [ ] 网格足够大，热图胜过线图。
- [ ] 大小量用顺序色图；带符号数据用**关于 0 居中**的发散色图。
- [ ] colorbar 带量和单位；同尺度面板共用一个。
- [ ] 轴刻度显示真实取值，不是下标。
- [ ] `interpolation="nearest"`；格子间无平滑。
- [ ] 混淆矩阵：caption 写明归一化方式，报告样本数。
- [ ] 失败/缺失运行与"差但真实"的取值在视觉上可区分。
