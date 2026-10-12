# Research Skills

一套与具体工具链解耦的通用科研全流程 [Agent Skills](https://github.com/openai/skills) 包，覆盖从找论文、设计实验、分析结果、诊断优化，到出版级出图和 LaTeX 论文写作的完整闭环。

所有技能都是纯 Markdown 指令 + 按需加载的 references，两个 Python 脚本仅依赖 Python 3 标准库，不需要 API key，也不绑定任何特定 CLI、平台或服务。

## 闭环流程

```text
literature-review       找论文 / 综述 / 核验引用
        |
        v
experiment-workflow     baseline / freeze / 实验树 / 固定 run contract
        |
        v
experiment-analysis     证据核验 / 多种子聚合 / 差值区间 / 即时决策
        |
        v
optimization-advisor    根因诊断 / 文献与社区调研 / 排序后的优化方案
        |
        v
experiment-workflow     用新实验验证方案（回到循环）
        |
        v
research-figures        出版级图（matplotlib / TikZ）
research-paper          LaTeX 论文 / 预印本
```

六个技能互相独立、按需触发，不依赖 umbrella/router；每个技能只做自己职责内的事，交接时传递结构化产物。

## 技能清单

| 技能 | 职责 | 典型触发 | 明确排除 |
|---|---|---|---|
| [`literature-review`](literature-review/SKILL.md) | 检索、阅读、去重、综合真实文献；综述、方法对比、引用/BibTeX 核验 | 找论文、related work、文献综述、引文核验、DOI/arXiv/PubMed | 一般网页调研、写 LaTeX 正文 |
| [`experiment-workflow`](experiment-workflow/SKILL.md) | baseline、freeze、Git 分支、固定 run contract、实验树、repair/refill/promote/stop | 对比实验、消融、调参、复现、AB 验证 | 一次性脚本、已有结果分析、方案设计 |
| [`experiment-analysis`](experiment-analysis/SKILL.md) | 运行证据核验、多种子聚合、差值/不确定性、消融归因、失败诊断、即时决策 | run logs、metrics、结果表、消融/对比结果分析 | 实际跑实验、外部根因调研、绘图 |
| [`optimization-advisor`](optimization-advisor/SKILL.md) | 结合结果与代码做根因诊断；查论文/文档/源码/issue/社区；输出排序后的修改方案 | “为什么效果不好”“怎么优化”“下一轮该试什么” | 单纯解释 run、单纯查论文、直接改代码/跑实验 |
| [`research-figures`](research-figures/SKILL.md) | 出版级 matplotlib/TikZ：视觉设计、印刷尺寸、统计表达、audit、矢量导出 | 为论文或报告画图、改图、评图 | 统计分析本身、论文结构写作 |
| [`research-paper`](research-paper/SKILL.md) | LaTeX 论文/预印本/章节：模板、结构、图表引用、参考文献、编译排错 | 写论文、手稿、arXiv/投稿草稿 | 普通报告、结果总结、文献检索本身 |

## 设计原则

1. **证据优先。** 结论必须能回溯到 run、配置、commit、日志行或真实文献记录；标题、作者、DOI、引用和数字不得凭记忆生成。
2. **职责单一。** 每个技能有明确边界和排除项，避免重复劳动或越权（例如 `optimization-advisor` 只做只读诊断，不改代码、不跑完整实验）。
3. **渐进披露。** `SKILL.md` 保持精炼，细节放在 `references/`，只在需要时读取；避免一次性加载全部上下文。
4. **可证伪。** 假设、修改方案、验证计划都要求明确预测、success criteria 和 stop/kill condition。
5. **可移植。** 不假设特定 CLI、目录结构或平台；运行命令、分支命名、产出目录优先沿用所在仓库的既有约定。
6. **按需脚本。** 复杂、重复且易错的计算封装成标准库脚本；其余部分保持纯指令。

## 目录结构

```text
research-skills/
├── LICENSE
├── README.md
├── literature-review/
│   ├── SKILL.md
│   ├── references/
│   │   ├── reading.md
│   │   ├── retrieval.md
│   │   └── synthesis.md
│   └── scripts/
│       └── scholarly_search.py
├── experiment-workflow/
│   ├── SKILL.md
│   └── references/
│       ├── delegation.md
│       ├── evidence.md
│       ├── runs.md
│       └── tree.md
├── experiment-analysis/
│   ├── SKILL.md
│   ├── references/
│   │   ├── decisions.md
│   │   ├── evidence.md
│   │   └── statistics.md
│   └── scripts/
│       └── analyze_runs.py
├── optimization-advisor/
│   ├── SKILL.md
│   └── references/
│       ├── diagnosis.md
│       ├── proposals.md
│       └── search-routing.md
├── research-figures/
│   ├── SKILL.md
│   ├── assets/
│   │   ├── figstyle.py
│   │   └── tikz-preamble.tex
│   └── references/
│       ├── comparison.md
│       ├── curves.md
│       ├── diagram.md
│       ├── matrix.md
│       ├── pareto.md
│       └── scaling.md
└── research-paper/
    └── SKILL.md
```

## 安装

### 方式一：克隆到通用 skills 目录（推荐）

```bash
git clone https://github.com/Jiayz00/research-skills.git ~/.agents/skills/research-skills
```

克隆后，将需要的技能目录软链接或复制到 harness 实际读取的 skills 目录。例如 Codex 默认读取 `~/.codex/skills/`：

```powershell
# Windows 示例：为每个技能建立 junction
$repo = "$env:USERPROFILE\src\research-skills"
$dst  = "$env:USERPROFILE\.codex\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
'literature-review','experiment-workflow','experiment-analysis','optimization-advisor','research-figures','research-paper' | ForEach-Object {
    New-Item -ItemType Junction -Path (Join-Path $dst $_) -Target (Join-Path $repo $_) -Force | Out-Null
}
```

```bash
# macOS / Linux 示例
repo=~/src/research-skills
dst=~/.codex/skills
mkdir -p "$dst"
for s in literature-review experiment-workflow experiment-analysis optimization-advisor research-figures research-paper; do
  ln -sfn "$repo/$s" "$dst/$s"
done
```

### 方式二：逐目录复制

把每个技能目录整体放进 harness 的 skills 目录即可。技能之间互相独立，可以只安装你需要的子集，但完整闭环需要六个全部安装。

### 验证安装

新开一个会话，确认技能列表中包含六个技能。也可以用 `skill-creator` 的校验脚本逐个检查：

```bash
python path/to/quick_validate.py literature-review
```

Windows 下建议先设置 `PYTHONUTF8=1`，避免中文 frontmatter 编码问题。

## 脚本用法

### 文献检索：`scholarly_search.py`

默认查询 OpenAlex、Crossref、arXiv、PubMed 四个公开数据源，无需 API key；单个源失败不影响其他源，错误写入输出中的 `errors` 字段。

```bash
python literature-review/scripts/scholarly_search.py \
  --query "retrieval augmented generation evaluation" \
  --sources openalex,crossref,arxiv,pubmed \
  --limit 10 --from-year 2020 --to-year 2026 \
  --rank relevance \
  --format markdown \
  --output artifacts/rag-eval/literature/review.md
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--query` | 检索词或完整研究问题（必填） |
| `--sources` | 逗号分隔的数据源，默认四源 |
| `--limit` | 最终返回条数，默认 10 |
| `--from-year` / `--to-year` | 年份过滤 |
| `--rank` | `relevance`（默认）/ `recency` / `citations` |
| `--format` | `json` / `markdown` / `bibtex` |
| `--output` | 输出文件；省略则打印到 stdout |
| `--timeout` | 单次网络请求超时秒数 |
| `--mailto` | 可选，OpenAlex/Crossref polite pool 联系方式 |

去重顺序为 DOI → arXiv ID → PMID → 归一化标题；每条记录保留全部来源 provenance。脚本只返回元数据和开放获取链接，不自动下载 PDF。

### 结果分析：`analyze_runs.py`

输入 tidy 格式的 CSV 或 JSONL，至少包含 `group` 和数值 `value` 两列；可选 `run_id`、`seed`、`step`、`cost`、`status`。

```bash
python experiment-analysis/scripts/analyze_runs.py \
  --input runs.csv \
  --group variant --value accuracy \
  --run-id run_id --seed seed \
  --baseline baseline \
  --confidence 0.95 --bootstrap 2000 --random-seed 0 \
  --format markdown --output artifacts/topic/analysis/analysis.md
```

输出包括：

- 每组统计量：n、mean、SD、置信区间；
- 相对 baseline 的 bootstrap 差值区间（配对/非配对自动选择）；
- 缺失值、重复 run、单种子、非有限值等警告；
- 每个结论对应的 run/seed provenance。

脚本只给出统计事实和警告；最终 `analysis.json`（含 `decision`、`confidence`、`evidence`、`next_actions`）由 `experiment-analysis` 技能根据证据写出。

## 产出目录约定

优先沿用所在仓库的既有约定；没有约定时使用：

| 类型 | 默认位置 |
|---|---|
| 运行日志 | `runs/` |
| 笔记 | `notes/` |
| 文献 | `artifacts/<topic>/literature/` |
| 分析 | `artifacts/<topic>/analysis/` |
| 优化建议 | `artifacts/<topic>/advice/` |
| 报告图 | `artifacts/<topic>/figures/` |
| 论文图 | `figs/` |
| 论文 `.tex` | 仓库根目录或既有 paper 目录 |

## 跨技能交接契约

| 从 | 到 | 传递内容 |
|---|---|---|
| `experiment-workflow` | `experiment-analysis` | run manifest：`run_id`、`variant`、`branch`、`commit`、`seed`、`log_path`、`command`、`status` |
| `experiment-analysis` | `optimization-advisor` | `analysis.json` + 日志与代码上下文 |
| `optimization-advisor` | `experiment-workflow` | `proposals.json` 中优先级最高、状态为 `proposed` 的方案 |
| `experiment-analysis` | `research-figures` | 验证过的 tidy 表格 |
| `research-figures` | `research-paper` | 图文件、caption 数据、生成脚本 |
| `literature-review` | `research-paper` | 真实文献记录、引用条目、BibTeX |

## 验证状态

发布前已完成以下检查：

- 六个技能全部通过 `skill-creator` 的 `quick_validate.py`；
- 六目录内无任何特定平台/CLI 残留标识或绝对路径；
- 两个 Python 脚本通过 `py_compile` 与 `--help`，并完成真实查询/分析 smoke test；
- `scholarly_search.py` 验证四源检索、跨源去重、多格式输出与部分源失败降级；
- `analyze_runs.py` 验证均值、置信区间、baseline 差值、单种子与重复 run 警告；
- 文献、分析、优化建议、端到端四条前向测试通过；
- 出图脚本 audit 为 clean，最小 LaTeX 文档可编译。

## 授权与引用

引用文献时请始终核实到真实记录与原文位置；本仓库不包含任何文献全文，只提供检索与综合方法。若在研究中使用了本套技能，欢迎在方法或致谢中说明。

## License

[MIT](LICENSE)

