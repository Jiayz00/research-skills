---
name: research-paper
description: 把研究结果写成 LaTeX 论文或预印本：在工作区创建可编译的 .tex 与 PDF，覆盖模板、结构、图表、文献与编译排错。适用于写论文、手稿、arXiv/投稿草稿或其中一个章节；文献检索用 literature-review，结果分析用 experiment-analysis，出图用 research-figures，普通报告/结果总结不触发。
---

论文写成工作区里真实的 `.tex` 文件，而不是聊天里的提纲。`.tex` 留在工作区（能被编辑、能被编译的位置，不要只放进产出目录）；PDF 与它同目录生成。

## 全流程 handoff

- 找论文、核验引用和 BibTeX：`literature-review`。
- 结果数字、差值、不确定性：`experiment-analysis`。
- 出版级图和 caption：`research-figures`。
- 需要新实验：`experiment-workflow`；未验证的优化方案只能放方法讨论或 future work，并明确标注未验证。

## 第一次请求就建文件

在仓库根放 `paper.tex`（多篇并存时用 `<topic>.tex`），直接写入真实内容，然后把渲染结果路径给用户。只在聊天里给提纲，用户拿不到可看的东西。

## 写前言之前先找模板

用户可能已有 LaTeX 模板（会议类、实验室预印本样式）。先找再写：

- 仓库里已有的模板：`*.cls`/`*.sty`/`*.bst`、`templates/`、`paper/`、投稿目录等；
- 用户明确提供过的模板路径。

规则：

- **恰好一个模板**——直接用，不要问。
- **多个**——列出名称问用哪个，除非请求里已说明。
- **没有**——用下面的默认前言。

用模板时：把它的 class 与样式文件拷到 `.tex` 旁边，从它的入口 `.tex` 起稿，保留它的 `\documentclass`、包列表和章节骨架，只替换占位内容。会议类文件编码了页边距、字体和匿名模式，是投稿要对照检查的——不要覆盖它。模板需要机器上没有的包时，如实说明，不要悄悄换回默认前言。

## 一个能编译的默认前言

没有模板时从这里开始，它覆盖下面所有章节的用法：

```latex
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{listings}
\usepackage{natbib}
\usepackage[hidelinks]{hyperref}
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}

\title{...}
\author{...}
\date{\today}

\begin{document}
\maketitle
...
\end{document}
```

**每个环境都需要定义它的包。** 这是草稿编译失败最常见的原因，而且是致命的、不是外观问题：

| 用到 | 需要 |
| --- | --- |
| `theorem`、`lemma`、`proof` | `amsthm` **且**每个都要 `\newtheorem` |
| `lstlisting` | `listings` |
| `align`、`equation*`、`\text` | `amsmath` |
| `\toprule`、`\midrule` | `booktabs` |
| `\includegraphics` | `graphicx` |
| `\url`、`\href` | `hyperref` |
| `\citet`、`\citep` | `natbib`（裸 `\cite` 不需要） |

只加载用到的包；绝不使用没有定义过的宏。

## 需要换引擎时要明说

论文默认 pdfLaTeX。需要 XeLaTeX 或 LuaLaTeX 的文档（`fontspec`、`unicode-math`、系统 OpenType 字体）必须在第一行声明，否则会用错引擎而失败：

```latex
% !TeX program = lualatex
```

其余情况不要加这一行：pdfLaTeX 支持面最广，`microtype` 的字距调整也只在它下有效。

## 结构

`\begin{abstract}`，然后 `\section`/`\subsection`。被引用的公式要编号（`\begin{equation}\label{eq:loss}`），用 `\eqref{eq:loss}` 引用；从不引用的公式用带星号形式。所有浮动体都加 `\label`，引用写 `Table~\ref{tab:main}`，绝不用"下页的表"——浮动体会移动。

## 图与表

作图前先读 `research-figures` 技能。把默认 matplotlib 输出直接丢进论文是审稿人会点名的缺陷：物理尺寸错、该放 caption 的地方放了标题、该矢量时栅格化。TikZ 方法图也在那个技能里，和论文一样在此工作区编译。

引用真实存在、路径相对 `.tex` 的图：

```latex
\includegraphics[width=\linewidth]{figs/loss_curve.pdf}
```

写全扩展名，引用前确认文件存在——缺图会挂编译。

## 参考文献

先读 `literature-review`：引用内容和 BibTeX 条目必须来自真实检索并核验。仓库或模板已有 `.bib`、biber 或 biblatex 工作流时沿用仓库约定；没有现成工作流时，默认用一遍编译的内联 `thebibliography`：

```latex
\begin{thebibliography}{9}
\bibitem[Kaplan et al.(2020)]{kaplan2020} Kaplan et al. Scaling laws for
  neural language models. 2020.
\end{thebibliography}
```

一遍编译就够。`\bibliography{refs}` + 独立 `.bib` 需要 biber 往返，在完成前一直显示未解析引用。

`[Author(Year)]` 标签就是 `\citet` 打印的内容；没有它 natbib 就没有名字可用。每条都要给——作者不详时用短标题，不要编造名字。

按句子的读法选引用命令：

- `\citet{kaplan2020}` —— 引用是主语：*Kaplan et al. (2020) show…*
- `\citep{kaplan2020}` —— 括号旁注：*…is predictable (Kaplan et al., 2020)*
- natbib 下裸 `\cite` 等价于 `\citet`，`GRPO~\cite{x}` 会印成 *GRPO Shao et al. (2024)*，没有括号。旁注要写 `\citep`。

用 `literature-review` 的检索与阅读协议找真实文献，并读原文。**编造引用比没有引用更糟。**

## 数字来自运行，不来自记忆

结果表里的每个数字都必须来自真实运行，并先经过 `experiment-analysis` 的证据核验和不确定性分析。原始日志作为 provenance，不直接凭记忆写正文。绝不写入看起来像真的占位数字；还没测的数字要在正文里说明。

## 文件怎么编译

工作区里的 `.tex` 用当前 harness 可用的编译能力——内置 LaTeX 编译器，或本机引擎 `tectonic`、`latexmk`、`pdflatex`——`paper.pdf` 写在源文件旁边。先探测可用的编译器再选（内置能力优先；CLI 可试 `tectonic --version`、`latexmk --version`，或用 `Get-Command` / `which` 查找）。

没有近似的预览可以退而求其次：编译不过的文档等于什么都没有。构建失败是"用户有论文/没有论文"的区别，不是记一笔就过的外观问题。

编译失败时，TeX 日志就是诊断：找第一行以 `!` 开头的错误，它给出问题和源行号——改源文件，让它重新构建。绝不交付编译不过的文档。

机器上没有任何 LaTeX 引擎时，直接说明，并给出可选项（安装 TeX 发行版、或把 `.tex` 交给 Overleaf 等在线编译）——不要假装文件已经完成。
