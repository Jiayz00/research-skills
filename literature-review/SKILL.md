---
name: literature-review
description: 检索、阅读并综合真实学术文献：论文搜索、related work、文献综述、方法对比、引用核验。适用于论文、预印本、DOI、arXiv、PubMed 等学术资料请求；一般网页/产品调研用 research/agent-reach，写 LaTeX 论文用 research-paper。
---

# 文献综述（literature review）

把“找资料”做成可核验的证据链：候选从哪里来、为什么入选、哪篇真正读过、每个结论对应哪条原文。论文标题、作者、DOI、引用次数和引文都不能凭记忆生成。

## 边界

- 用于学术文献：论文、预印本、学位论文、技术报告、系统综述、DOI/arXiv/PubMed 记录。
- 一般网页、产品资料、社区讨论：如果本机有 `research`/`agent-reach` 技能就优先用，否则用 harness 自带搜索；不要伪装成同行评议文献。
- 写 LaTeX、组织参考文献章节：加载 `research-paper`；本技能负责找到并核验引用，不负责论文结构。
- 做实验结果分析：加载 `experiment-analysis`；本技能只在需要外部方法/理论证据时提供文献。

## 核心原则

1. **真实优先（authenticity first）**：只报告实际检索到的记录；不得补全、猜测或凭印象生成 DOI、作者、年份、引用数。
2. **claim-level support**：摘要/snippet 只能做候选发现；把某篇论文当作主张证据前，必须读原文的相关段落、图表或方法部分。
3. **provenance 保留**：每条记录保留来源（OpenAlex、Crossref、arXiv、PubMed、连接器）和原始链接；多个来源合并时不要丢掉来源。
4. **版本意识**：预印本、会议版、期刊版可能不同；引用时说明版本，不要拿另一版本的结果冒充目标版本。
5. **检索有预算**：先追求覆盖，再停止；不做无休止的同义改写。默认 difficulty 1–10 映射到 0/1/2 个 follow-up rounds，硬上限见 `references/retrieval.md`。
6. **引用可核验**：引用必须能回到真实记录和原文位置；没有找到合适证据时，明确说“没找到”，不要用熟悉的名字填空。

## 检索循环

1. **定 scope**：问题、领域、时间窗口、语言、venue、需要的证据深度。
2. **建 query**：先保留用户原始术语；精确关键词用方法名、缩写、benchmark、标题短语；语义查询用一句忠实问题。不要猜缩写全称。
3. **选源**：OpenAlex 做跨学科/引用图谱，Crossref 做 DOI/期刊元数据，arXiv 做 CS/物理/数学预印本，PubMed 做生物医学/生命科学；bioRxiv 通过 OpenAlex 覆盖。具体路由见 `references/retrieval.md`。
4. **检索与去重**：各源独立执行；失败源记录错误，不丢弃其他源结果。按 DOI → arXiv ID → PMID → normalized title 去重。
5. **排序与筛选**：topical fit 是第一信号；recency/citations 按用户要求调整。不要拿不同源的 votes/citations 直接比较。
6. **读原文**：选出 3–5 篇最 load-bearing 的论文，读方法、结果、限制和图表。阅读协议见 `references/reading.md`。
7. **综合**：选择输出模式——ranked discovery、annotated bibliography、related work、method comparison、gap analysis、BibTeX。模式与模板见 `references/synthesis.md`。
8. **核验**：交付前逐条检查引用链接、版本、作者/年份、是否与句子中的 claim 对齐。

## 检索脚本

没有现成学术连接器时，使用本技能的 stdlib-only 脚本：

```sh
python <本技能目录>/scripts/scholarly_search.py \
  --query "..." \
  --sources openalex,crossref,arxiv,pubmed \
  --limit 10 --format json
```

- `--rank relevance|recency|citations`：默认 relevance。
- `--format json|markdown|bibtex`：JSON 适合后续处理，Markdown 适合阅读，BibTeX 适合交给 `research-paper`。
- `--from-year`/`--to-year`：可选的包含边界。
- `--mailto`：可选，OpenAlex/Crossref 的 polite pool 联系方式。
- 任一数据源不可达时，输出仍包含 `errors` 和其他源的部分结果；不要因为一个源失败就伪造结果或停止整个检索。
- 没有网络或没有可用 API 时，改用 harness 自带的网页/学术工具；仍按本技能的检索、去重、阅读和引用规则执行。

## 输出与存放

- 先看仓库既有 convention：`notes/`、`docs/`、`literature/` 或论文目录。
- 无约定时写到 `artifacts/<topic>/literature/`：
  - `candidates.json`：脚本或手工整理的候选记录；
  - `review.md`：综述/对比/相关工作总结；
  - `refs.bib`：论文写作需要的 BibTeX。
- 聊天回答用紧凑结构：结论、证据、出处、限制；不要贴无关的论文清单。
- 链接用真实 landing page/DOI/PubMed/arXiv；不要用搜索页或伪造的全文链接。

## 子代理

- 检索循环、候选排序和最终引用核验留在主代理。
- 可以把“已选定论文的独立阅读、结构化摘要、交叉核对”委派给子代理，但必须检查它引用的原文位置，不能直接把子代理生成的引用交付。
- 用完的子代理及时关闭，不堆积。

## 深入

- 数据源、query、预算、去重与失败处理：`references/retrieval.md`
- 读原文、提取证据、版本与引用：`references/reading.md`
- 综述/对比/引用输出模板：`references/synthesis.md`
- 论文写作 handoff：`research-paper`
- 实验方法/结果分析 handoff：`experiment-analysis`、`optimization-advisor`