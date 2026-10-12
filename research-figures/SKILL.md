---
name: research-figures
description: 出版级图表（matplotlib 或 TikZ）：学习曲线、scaling、对比与消融、Pareto、热图与矩阵、方法示意图；含统一样式模块、印刷尺寸、不确定性与矢量导出。为论文或报告画图、改图、评价图是否够精时使用；写绘图代码之前先读它；统计聚合与不确定性由 experiment-analysis，论文结构由 research-paper。
---

论文里的一张图是一个**论证**，不是数组的截图。它只主张一件事，跳读正文的读者也应该正确得到这个主张。默认的 matplotlib 输出达不到这个标准：尺寸为屏幕而定、用标题占了 caption 的位置、配色在灰度下塌掉、该矢量时却栅格化。

下面这些，是"经得住审稿的图"与"deadline 前一周返工的图"之间的区别。

## 上游数据与分析边界

- 统计聚合、差值区间、离群/失败判断：先读 `experiment-analysis`，不要在这里重新定义口径。
- 本技能负责：图型选择、尺寸、配色、caption、矢量导出和 audit。
- 还没有验证过的运行数字：先回到 `experiment-analysis`；没有分析就画图，等于把未核验数字交付出去。
- 图用于论文：先读 `research-paper` 的模板/栏宽/引用约定；图与 caption 一起写。
- 需要新的实验来支撑图上的主张：回到 `experiment-workflow`，不要在图脚本里改实验数据。

## 不可妥协项（non-negotiables）

1. **按最终印刷尺寸作图。** 画成 8 英寸再缩进 3.25 英寸的栏，刻度标签只剩 3pt。先按文档定宽度（样式模块里的 `COLUMN`、`TEXT`、`WIDE`），再用 `width=\linewidth` 插入——尺寸对了它按 1.0 缩放、什么也不改（见"图放哪里"）。绝不要画大再缩。`WIDE` 的图只有在 `figure*` 环境里才拿得到 6.75 英寸的 `\linewidth`；双栏论文的普通 `figure` 里它会悄悄缩到一半左右。
2. **矢量输出。** 给 `\includegraphics` 写 PDF，同时写一份 SVG 用于预览。**绘图内容**（坐标轴、线、文字）被栅格化是缺陷：审稿人放大看时它会糊。PNG 只适合真栅格内容：照片、样本图网格、像素级 attention map。
3. **每个数字都来自真实运行。** 统计聚合、差值区间和离群/失败判断先由 `experiment-analysis` 完成；本技能从它验证过的 tidy 数据或原始运行日志取数。绝不画记忆里的、四舍五入过的或“看起来合理”的数字；也不要把合成演示数据留在要交付的脚本里。
4. **caption 就是标题。** 论文图不加 `ax.set_title`——它与 caption 重复还偷纵向空间。多面板图用面板字母（**a**、**b**）命名各部分。
5. **展示不确定性，或明确说明没有。** 单种子是轶事。画多种子的区间，并在 caption 里写明种子数；只有一次运行就写 "single seed"，不要暗示更多。
6. **坐标轴带单位。** "Loss" 是标签；"step" 不说明它数的是优化步还是 token，就等于没写。
7. **色盲安全、灰度安全。** 用样式模块的调色板。绝不用 `jet`、`rainbow`、`hsv`——它们会编造数据里没有的结构。
8. **无衬线字体，且所有图同一字面。** `use_style()` 默认 Helvetica 度量的无衬线（Nature/Science 对图的要求），也扛得住 5–8pt 的刻度字号。图的文字自成一套 register：不必与正文一致，但必须与你的所有图（含示意图）一致。只有当图承载大量数学、希望读起来像衬线排版页面时，才用 `use_style(family="serif")`。

## 每个项目只配置一次

把样式模块拷贝到绘图脚本旁边，让图在会话结束后仍然可复现：

```sh
mkdir -p figs && cp <本技能目录>/assets/figstyle.py figs/figstyle.py
```

`<本技能目录>` = 加载本技能时给出的目录（SKILL.md 所在目录）。拷贝到脚本所在的目标目录旁边——报告脚本在产出目录里，就也要在那里放一份，否则 import 失败。导入前确认文件非空。

Python 环境按仓库既有约定（venv / uv / conda）。模板依赖 `matplotlib` 与 `numpy`。独立脚本可用：

```sh
uv run --no-project --with matplotlib --with numpy python figs/loss_curve.py
```

带内联依赖元数据的脚本用 `uv run --no-project figs/loss_curve.py`。需要 import 项目代码的脚本必须在项目环境里跑，不能用上面的隔离环境。

## 图放哪里、怎么引用

两种去处，引用方式不同；配错是"图到用户手里变成坏链接"的最常见原因。

| 图用于 | 写到 | 引用为 |
| --- | --- | --- |
| 论文（`.tex`） | 与 `.tex` 同目录的 `figs/`——`\includegraphics` 按源文件相对路径解析 | 仓库相对路径，如 `figs/loss_curve.pdf`（**不要**加 `artifacts/` 前缀） |
| 报告、总结、聊天回答 | 产出目录里对应的主题/交付物文件夹（见 `experiment-workflow` 的 evidence 约定），如 `transformer-sweep/figures/` | 完整路径，如 `artifacts/transformer-sweep/figures/loss_curve.pdf` |

**引用路径必须与存放位置一致。**

**只有这两种去处。** 不要把要引用的图写进 `/tmp`、scratch 目录或这两个根之外的地方；日志或中间数据放 `/tmp` 没问题——图不行，生成它的脚本也不行。

生成脚本与产物放在一起（`figs/loss_curve.py` → `figs/loss_curve.pdf`、`figs/loss_curve.svg`）。脚本丢了，审稿人要补一个种子时这张图就无法修正。

按栏宽作图，**同时**仍然写 `width=\linewidth`：

```latex
\begin{figure}[t]          % 双栏论文的 WIDE 图用 figure*
  \centering
  \includegraphics[width=\linewidth]{figs/loss_curve.pdf}
  \caption{Validation loss over training, mean of 5 seeds with 95\% intervals.}
  \label{fig:loss}
\end{figure}
```

两件事要一起做。尺寸对了，`width=\linewidth` 按 1.0 缩放、什么也不改——但万一期刊栏宽比你假设的窄，它还能兜住。它救不了尺寸本身就错的图：15 英寸画布塞进 5.5 英寸栏会缩到 0.35，11pt 刻度变 4pt。这是真实论文里图不可读的头号原因，而 `width=\linewidth` 会一直藏到付印。

## caption 与图同时写

下面每个 reference 都会说"在 caption 里写明"。意思就是这一节——caption 与图**一起**写，不是等稿子成型后补。

当前论文的 caption 中位数约 28 词，一半是三句以上。主流形态是**先一句加粗短句说明主张，再给读者信任它所需的细节**：

```latex
\caption{\textbf{LPO reaches the reward plateau in a third of the compute.}
Held-out reward against training compute for LPO and two baselines; mean of 5
seeds, bands are 95\% intervals. The dotted line is the pretrained model.}
```

- **先给发现，不是设置。** "Training curves for LPO and baselines" 是在复述坐标轴。第一句应该写你想让人记住的东西。
- **图要能独立成立。** 跳过正文第 4 节的读者也应该把主张理解正确——这就是全部要求。
- **方法性事实放这里**，图的别处没有空间：种子数、band/bar 的含义、平滑与归一化、哪些点参与拟合哪些被排除、前沿线是实测还是示意。
- **没展示的东西要说明**（重要时）：单种子、截断的轴、提前终止的运行。
- **不要复述坐标轴标签**，也不要把 caption 重复成 axes title。

单面板图约 25–40 词；多面板图更多，每个面板都要有自己的短句。

## 多面板图

- **每个面板都标字母** `(a)`、`(b)`…（`panel_labels()`），正文才能写 "Fig. 2b"。
- **共享量就共享轴**（`sharey=True`），只在一处显示刻度。同一指标在面板间用不同范围，是"截断柱状轴"的多面板版本——读者在比较不可比的高度。
- **整图一个图例**，不要每个面板一个；放在面板下方或最后一个面板外侧。
- **面板按论证顺序**：从左到右、从上到下；(a) 是正文最先讨论的那个。
- **不支持同一个主张的面板，就该拆成两张图。** 2×3 的不相关拼盘是 contact sheet，caption 会写成清单而不是句子。

用 `figure_grid(nrows, ncols, width=TEXT, sharey=True)` 构建，它会把整个网格按最终印刷宽度定尺寸。

## 只读一个 reference

按"图要回答的问题"选，不是按你脑子里的图形选。

| 图回答的问题 | 读 |
| --- | --- |
| 指标随训练怎么变？差距大过种子噪声吗？ | [references/curves.md](references/curves.md) |
| 性能随规模怎么变？趋势外推指向什么？ | [references/scaling.md](references/scaling.md) |
| 哪个方法在多个 benchmark 上赢？消融里哪个组件起作用？ | [references/comparison.md](references/comparison.md) |
| 在什么和什么之间取舍——reward vs KL、质量 vs 成本/延迟？ | [references/pareto.md](references/pareto.md) |
| 这个二维网格、混淆矩阵或 sweep 长什么样？ | [references/matrix.md](references/matrix.md) |
| 方法、结构或流水线是什么？ | [references/diagram.md](references/diagram.md) |

每个 reference 的模板默认写 `figs/`（论文目的地）。给报告或聊天回答用时，把脚本与输出路径改到产出目录对应文件夹。

不做的图不读。reference 读不到就直接读本技能目录下的 `references/<name>.md`。

六类之外的图（照片、定性样本网格、地图）仍然遵守上面的不可妥协项与样式模块。

## 交付前检查

- **读 `save()` 打印的 audit 行。** 它检查印刷宽度、Type 42 字体嵌入、多余的 axes title、缺失的轴标签、低于 5pt 的文字、文字重叠与出血。`clean` 是及格线；其他都是要修的缺陷，不是"记一下继续走"的警告。
- audit 报"机器上没有出版字体"时不要自己装字体——如实告诉用户（改环境要先问）。
- 参考线或数据点旁的标签是重叠的常见来源；移动它，或加 `backgroundcolor="white"` 遮罩。
- 打开 PDF 按印刷尺寸读一遍：屏幕上 100% 都看不清的刻度，印出来也不清。
- 每个轴有标签和单位；没有多余的 `ax.set_title`。
- caption 的主张不看正文也能从图里看出。
- 不确定性已展示，n 已写明。
- 没有无法解释的序列，没有已删内容的图例项。
- 脚本能从零重跑，产出同一个文件。

## Handoff

- 需要统计/差值/不确定性：`experiment-analysis`
- 需要 Methods/Results 的 LaTeX 结构与引用：`research-paper`
- 需要新实验：`experiment-workflow`
- 需要外部方法/优化建议：`optimization-advisor`
