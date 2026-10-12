# Scaling law

**回答：** 指标随模型规模、数据或算力怎么变；趋势在没跑过的规模上预测出什么。

图本身是实测点的 log-log 散点 + 一条拟合的幂律。它的全部价值在拟合上，所以拟合必须站得住：log 轴上四个点连一条直线，无论有没有意义，看起来都很有说服力。

## 拟合本领域使用形式

有下界的指标（loss、error）用两参数幂律 `L = A·N^(-α)` 是错的——它在 N 大时趋向 0，而真实 loss 不会。拟合三参数形式：

```
L(N) = E + A · N^(-α)
```

`E` 是不可约损失（数据的熵、Bayes 误差）。强行令 `E = 0` 会掰弯拟合、压平 `α`——而 `α` 正是你要报告的参数。`E` 也要拟合；误差对 `L` 拟合，不要对 `log(L - E)` 拟合（后者被最贴近下界的那些运行支配）。如果拟合出的 `E` 落在 0 或 `min(L)` 上，说明这些运行约束不住下界：如实说明，不要把边界值当测量结果报告。

`α` 要带区间（对运行做 bootstrap 就够），写进图里而不只是正文。没有不确定度的 scaling 指数会招来审稿人反问：这是几个点拟合出来的？

## 什么点进拟合

- **只用一个 regime。** 训练不足的、被 warmup 限制的、撞上其他瓶颈的运行属于另一条 law。有意思可以画，但排除出拟合，并说明哪些点参与了。
- **至少 4 个点，最好跨一个数量级以上。** 少于 4 个、或全在 3 倍范围内，那是趋势线不是 scaling law——按趋势线标注。
- **可比的运行。** 同数据、同 tokenizer、同评测。拿两套评测集混进一张 scaling 图，是"看起来没问题"的坏图。

## 外推必须看起来像外推

如果图的意义在于预测没跑过的规模：拟合范围内实线，范围外虚线，并给外推区域加底纹。一条实线冲出图的右边界，等于在没有测量的地方声称测量。

## 陷阱

| 陷阱 | 修法 |
| --- | --- |
| 刻度标签写成 `10^8`、`10^9` | 网格用十的幂没错；标签写成 `100M`、`1B`（`si_ticks`） |
| 画了拟合线但隐藏残差 | 主面板下面加残差条——那里出现弯曲说明形式错了 |
| 分不清哪些点参与拟合 | 参与点实心、排除点空心，并在 caption 说明 |
| 双 log 轴但只标了一个 | log 轴在这里是惯例，但单位仍要写 |
| `α` 只写在 caption | 把拟合方程打进面板——它就是结果 |
| 不同模型族用同一个颜色 | 每个族一种 marker 形状；族之间 law 可能不同 |

## 模板

`figs/scaling.py`，读取 `figs/scaling.csv`（`family,n_params,loss,fit`），`fit` 为 `1` 表示该点参与拟合：

```python
"""Loss vs. parameters with a fitted power law. Regenerate: python figs/scaling.py"""

import csv

import numpy as np
from figstyle import BASELINE, PALETTE, TEXT, figure_grid, save, si_ticks, use_style

DATA = "figs/scaling.csv"
PREDICT_TO = 1e11  # extrapolate the fit out to this many parameters


def load(path):
    n, loss, fitted, family = [], [], [], []
    with open(path) as handle:
        for row in csv.DictReader(handle):
            n.append(float(row["n_params"]))
            loss.append(float(row["loss"]))
            fitted.append(row["fit"] == "1")
            family.append(row["family"])
    return np.array(n), np.array(loss), np.array(fitted), np.array(family)


def fit_power_law(n, loss, alphas=np.linspace(0.02, 1.5, 800)):
    """Least squares for L = E + A*N^-alpha.

    For a fixed alpha the model is linear in (E, A), so scanning alpha and
    solving each slice exactly needs no nonlinear optimizer. It also fits the
    error on L rather than on log(L - E), which is dominated by whichever runs
    sit closest to the floor and collapses the fit to E = 0.
    """
    best = None
    for alpha in alphas:
        design = np.stack([np.ones_like(n), n**-alpha], axis=1)
        coef, *_ = np.linalg.lstsq(design, loss, rcond=None)
        if coef[0] < 0 or coef[1] <= 0:
            continue  # a negative floor or amplitude is not a scaling law
        sse = float(((design @ coef - loss) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, float(coef[0]), float(coef[1]), float(alpha))
    if best is None:
        raise ValueError("no fit with a non-negative irreducible term")
    _, e, a, alpha = best
    return e, a, alpha


def bootstrap_alpha(n, loss, draws=200, seed=0):
    rng = np.random.default_rng(seed)
    alphas = []
    for _ in range(draws):
        idx = rng.integers(0, len(n), len(n))
        if len(set(idx.tolist())) < 3:
            continue
        try:
            alphas.append(fit_power_law(n[idx], loss[idx])[2])
        except ValueError:
            continue  # a degenerate resample is not a reason to lose the figure
    if len(alphas) < draws // 4:
        raise ValueError(f"only {len(alphas)}/{draws} resamples fit; too few runs for an interval")
    return np.percentile(alphas, [2.5, 97.5])


def main():
    use_style()
    n, loss, fitted, family = load(DATA)
    e, a, alpha = fit_power_law(n[fitted], loss[fitted])
    lo, hi = bootstrap_alpha(n[fitted], loss[fitted])

    fig, (ax, res) = figure_grid(
        nrows=2, ncols=1, width=TEXT, ratio=0.62,
        sharex=True, gridspec_kw={"height_ratios": [3, 1]},
    )

    def curve(x):
        return e + a * x**-alpha

    measured = np.geomspace(n[fitted].min(), n[fitted].max(), 100)
    beyond = np.geomspace(n[fitted].max(), PREDICT_TO, 100)

    ax.plot(measured, curve(measured), color=BASELINE, zorder=1)
    ax.plot(beyond, curve(beyond), color=BASELINE, linestyle="--", zorder=1)
    ax.axvspan(n[fitted].max(), PREDICT_TO, color=BASELINE, alpha=0.08, linewidth=0)

    markers = ("o", "s", "^", "v", "P", "X")
    families = sorted(set(family))
    if len(families) > len(markers):
        raise ValueError(f"{len(families)} families, {len(markers)} markers: add more")
    for marker, name in zip(markers, families):
        pick = family == name
        ax.scatter(n[pick & fitted], loss[pick & fitted], marker=marker,
                   color=PALETTE["blue"], label=name, zorder=2)
        ax.scatter(n[pick & ~fitted], loss[pick & ~fitted], marker=marker,
                   facecolor="none", edgecolor=PALETTE["blue"], linewidth=0.7, zorder=2)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylabel("Validation loss")
    ax.set_xlim(right=PREDICT_TO)
    ax.text(
        0.03, 0.06,
        rf"$L = {e:.2f} + {a:.1f}\,N^{{-{alpha:.3f}}}$" "\n"
        rf"$\alpha \in [{lo:.3f},\ {hi:.3f}]$, {int(fitted.sum())} runs",
        transform=ax.transAxes, va="bottom", fontsize=7,
    )
    if len(set(family)) > 1:
        ax.legend(loc="upper right")

    res.axhline(0, color=BASELINE, linewidth=0.6)
    res.scatter(n[fitted], 100 * (loss[fitted] - curve(n[fitted])) / loss[fitted],
                color=PALETTE["blue"], s=8)
    res.set_ylabel("Resid. (%)")
    res.set_xlabel("Non-embedding parameters")
    si_ticks(ax, "y")
    si_ticks(res, "x")

    save(fig, "figs/scaling")


if __name__ == "__main__":
    main()
```

## 检查清单

- [ ] 拟合形式含不可约项，且报告了 `E`。
- [ ] `α` 带区间，参与拟合的运行数已写明。
- [ ] 被排除的点视觉上可区分，排除理由充分。
- [ ] 外推区域虚线 + 底纹；没有实线离开数据范围。
- [ ] 残差面板显示拟合没有系统性弯曲。
- [ ] 刻度读作 `100M` / `1B`，不是 `10^8`。
