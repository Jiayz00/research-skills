# 方法与架构示意图（TikZ）

**回答：** 方法**是什么**——流水线、架构、贡献位于其中何处。

示意图用 TikZ 画：它是矢量的，文字与论文同一排版引擎，能在 git 里 diff，审稿人说"把 loss 项挪个位置"你改一行就行，而不是重画。分工要干净：**示意图用 TikZ，数据图用 matplotlib。** 用 pgfplots 画柱状图等于多维护一套绘图栈，毫无收益。

无论用什么画，示意图必须真正矢量（PDF，不是画布的 PNG），并按其最终印刷宽度绘制——与这里每张图相同的两条规则。在此之上，TikZ 是推荐而非惯例：多数 ML 论文的示意图来自绘图工具。图偏插画性质时用绘图工具；方块、箭头、符号为主时（大多数方法图）用 TikZ。

## 从共享脚手架开始

`assets/tikz-preamble.tex` 定义 block、data、箭头与 stage 样式，以及和数据图相同的调色板。路径相对本技能的 SKILL.md。把它拷贝成示意图 `.tex` 的开头：

```sh
mkdir -p figs && cp <本技能目录>/assets/tikz-preamble.tex figs/method.tex
```

工作区里的 `.tex` 在其所在处编译，`figs/method.tex` 会在旁边产出 `figs/method.pdf`，直接可以 `\includegraphics`。编译与引擎选择见 `research-paper` 技能。

## 永远相对定位

用 `positioning` 库——`right=of encoder`、`below=4mm of loss`——绝不用绝对坐标。绝对坐标拼出来的图，每次某个框改名都要重建；相对定位的图会自己重排。这是"审稿后你会更新的图"与"你不会更新"之间的区别。

## 一个强调色，一个方向

- **贡献是唯一被强调的元素。** 其余全部用中性的 `block` 或 `muted` 样式。五个东西都有颜色的图，等于没告诉读者哪个是新的。
- **一个流向**：从左到右，或从上到下。回流的箭头必须**故意**看起来不同（`backflow`——梯度、stop-gradient、教师信号），而不是因为排版没地方了。
- **形状承载类型**：矩形是计算，梯形（`data`）是张量与数据集，虚线框（`stage`）分组阶段。

## 尺寸，以及 `scale` 陷阱

`\begin{tikzpicture}[scale=0.8]` 缩放的是**坐标**而不是节点文字，于是框收紧了、字还是原来大小，最后撞在一起。`transform shape` 会连文字一起缩——然后文字比 caption 还小，正是前面明令禁止的事。

按最终印刷宽度画图。太宽就缩短标签、换行布局、砍掉一个阶段。不要缩，也不要靠 `width=\linewidth` 把画宽的图压回来——那正是这条规则要防的"用缩放兜底"。插图前检查编译出的 PDF 实际宽度。

## 标注边

箭头上的张量形状、loss、维度（`edgelbl`）是最便宜的可读性收益：能跟上形状的读者可以不看正文重建方法。边上标一个 `$B\times T\times d$`，正文里就少一句话。

## 陷阱

| 陷阱 | 修法 |
| --- | --- |
| 用 `scale=0.7` 硬塞 | 按目标宽度重画；缩短标签 |
| 绝对坐标 `\node at (3.4, -1.2)` | `positioning`：`right=of prev` |
| 图里放标题节点 | caption 就是标题；删掉 |
| 每个框都不同颜色 | 贡献一个强调色，其余中性 |
| `\tikzexternalize`、`pgfplots` 外置化、`minted` | 通常不可用——外置化需要 shell escape，多数编译环境默认禁用 |
| 无理由的箭头交叉 | 重排节点；交叉必须意味着什么 |
| 图里文字比 caption 还小 | 节点用 `\footnotesize`，边标签 `\scriptsize`，不再往下 |

## 模板

`figs/method.tex` —— 共享脚手架 + 图：

```latex
% ... contents of tikz-preamble.tex above this line ...

\begin{document}
\begin{tikzpicture}[fig]

  \node[data]  (x)        {Batch\\$B\times T$};
  \node[block, right=of x]        (enc)  {Encoder\\$L$ layers};
  \node[ours,  right=of enc]      (mod)  {Adaptive\\router};
  \node[block, right=of mod]      (dec)  {Decoder};
  \node[data,  right=of dec]      (yhat) {Logits\\$B\times T\times V$};

  \draw[flow] (x)   -- node[edgelbl, above] {$B\times T$} (enc);
  \draw[flow] (enc) -- node[edgelbl, above] {$B\times T\times d$} (mod);
  \draw[flow] (mod) -- (dec);
  \draw[flow] (dec) -- (yhat);

  \node[muted, below=6mm of dec] (loss) {Cross-entropy};
  \draw[flow]     (yhat.south) |- (loss.east);
  \draw[backflow] (loss.west)  -| node[edgelbl, pos=0.25, below] {$\nabla$} (mod.south);

  \begin{scope}[on background layer]
    \node[stage, fit=(enc)(mod)(dec)] (trunk) {};
  \end{scope}
  \node[stagelbl, above=1mm of trunk] {trained end-to-end};

\end{tikzpicture}
\end{document}
```

按目标宽度画好，用 `width=\linewidth` 插入，与其他图完全一致：

```latex
\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{figs/method.pdf}
  \caption{The router replaces the fixed gate in the decoder trunk; gradients
  reach it through the standard cross-entropy path.}
  \label{fig:method}
\end{figure}
```

想把图直接内联到论文里：把 `\usepackage{tikz}`、`\usetikzlibrary{...}`、`\definecolor` 与 `\tikzset` 块移进论文前言，再 `\input` `tikzpicture` 主体。漏掉库论文就编译不过：`trapezium`、`Stealth`、`fit=`、`on background layer` 各来自其中一个库。**不要**把 `\familydefault` 带过去——无衬线字面挂在 `fig`、`edgelbl`、`stagelbl` 样式里，随图走、不碰别的。

## 检查清单

- [ ] 所有节点用 `positioning` 放置，没有绝对坐标。
- [ ] 恰好一个被强调的元素，且它是贡献。
- [ ] 一个流向；非正向的边有对应的样式。
- [ ] 需要时边上标注形状或量。
- [ ] 没有 `scale=`；编译出的 PDF 已经是目标宽度。
- [ ] 没有标题节点；解释由 caption 承载。
- [ ] 能编译，且你亲眼看过 PDF。
