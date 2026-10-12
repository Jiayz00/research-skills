# 检索（retrieval）

## 数据源矩阵

| 数据源 | 强项 | 适用问题 | 注意 |
| --- | --- | --- | --- |
| OpenAlex | 跨学科论文图谱、引用数、开放获取链接 | 期刊/会议论文、跨领域检索、引用关系 | 引用数高不等于 topical fit 高；不要把 citations 当唯一排序 |
| Crossref | DOI、期刊、作者、出版元数据 | 已知标题/DOI 补全、正式出版记录 | 摘要覆盖不稳定；不要从缺失字段推断信息 |
| arXiv | CS/物理/数学/统计预印本、版本历史 | 最新方法、预印本、会议前工作 | 预印本可能与正式版不同；引用时标注版本 |
| PubMed | 生物医学/生命科学期刊、MeSH | 医学、临床、生物、生命科学 | 不是所有主题都适用；没有引用数 |
| bioRxiv | 生命科学预印本 | 生物/医学最新预印本 | 通过 OpenAlex 的来源过滤覆盖，不单独实现搜索适配器 |

- 先用领域路由：CS/ML/物理/数学优先 arXiv + OpenAlex；生物医学优先 PubMed + OpenAlex；跨学科优先 OpenAlex + Crossref。
- 用户给了 DOI/arXiv ID/PMID 时，先做 exact lookup，再决定是否扩展检索。
- 如果 harness 有专门的学术连接器（例如可用学术搜索 API），优先使用连接器，但仍遵守本文件的去重、provenance 和阅读规则。

## Query 构造

- 保留用户原始术语和拼写；不要自作主张改写领域词。
- 精确关键词：方法名、模型名、benchmark、数据集、作者、标题短语、缩写。
- 语义查询：一句忠实问题，不要堆同义词；不要用通用填充词（“最新进展”“全面综述”）。
- 第一次检索不要猜缩写全称；把缩写原样检索，再根据返回结果确认全称。
- 时间窗口是约束，不是排序偏好：用户说“近两年”就不要偷偷放宽；用户没给窗口就不要凭空加 cutoff。
- 记录实际执行的 query、窗口、排序策略，方便复核。

## 排序与窗口

- 默认 relevance：topical fit 第一。
- `recency`：用户明确要最新工作时使用；不要把奠基性但较旧的工作直接排除。
- `citations`：用户要高影响力/流行度时使用；Crossref/PubMed 可能没有引用数，不要把缺失当 0。
- `from-year`/`to-year` 是包含边界；一轮检索确定后，follow-up rounds 继承同一窗口和排序，不要在中途偷偷改变。
- 不同源的 score/vote/citation 不可通约；按来源保留排序，不要伪造跨源统一分数。

## 检索预算

先估算 difficulty（1–10）：

| difficulty | follow-up rounds |
| --- | --- |
| 1–3 | 0 |
| 4–7 | 1 |
| 8–10 | 2 |

- 初始轮已经给出足够覆盖时立即停止；预算是硬上限，不是目标。
- 一个 follow-up round 只解决一个明确缺口：缺失缩写、方法名、benchmark、组织/作者、标题短语或子主题。
- 不要只用同义改写重复同一轮；同一缺口的多个 source 调用算一个 round。
- 两个完整 loop 后仍有完全不同的主题，可以降级为 shallow mode（只做初始检索，不再 follow-up）；不要无限扩展。

## 去重与合并

按优先级匹配：

1. 精确 DOI（lowercase，去掉 `https://doi.org/` 前缀）；
2. arXiv ID（去掉版本号后比较）；
3. PMID；
4. normalized title（小写、去标点、压缩空白）。

合并时：

- 保留所有来源和每个来源内的排名；
- 缺失字段用其他来源补全，但不要覆盖已核验的 DOI/版本；
- 摘要取信息更完整的一份，并保留来源；
- 引用数只保留原来源的数值和来源标签，不要相加；
- 版本不同（预印本 vs 期刊版）不要仅因标题相同就静默合并；在备注中保留版本关系。

## 失败处理

- 每个数据源独立请求；某一源失败时记录 `source`、错误类型和可操作的下一步，继续输出其他源结果。
- 超时/限流/网络错误可以重试一次；不要无限重试，也不要因此编造记录。
- 返回空集合只说明“这次 query + 窗口 + source 没有结果”，不证明该主题没有文献。
- 如果某个 source 的 top-N 明显偏题，不要用它们填满候选；改用 exact title/ID lookup、缩小 query 或换 source，并在输出里说明该源的覆盖不足。
- 不要在用户明确禁用某来源时绕过限制；改用允许的来源或如实说明缺口。

## 内置脚本

```sh
python scripts/scholarly_search.py \
  --query "retrieval augmented language model" \
  --sources openalex,crossref,arxiv,pubmed \
  --limit 10 \
  --from-year 2022 \
  --rank relevance \
  --format json \
  --output artifacts/topic/literature/candidates.json
```

参数：

- `--query`：必填，原始检索词或一句忠实问题。
- `--sources`：逗号分隔；默认 `openalex,crossref,arxiv,pubmed`。
- `--limit`：最终返回条数。
- `--from-year`、`--to-year`：可选年份边界。
- `--rank`：`relevance`、`recency`、`citations`；默认 relevance。
- `--format`：`json`、`markdown`、`bibtex`；默认 json。
- `--output`：可选输出路径；不写则打印到 stdout。
- `--timeout`：单请求超时秒数；默认 20。
- `--mailto`：可选礼貌池联系方式。

JSON 顶层结构：

```json
{
  "query": "...",
  "sources_requested": ["openalex", "crossref"],
  "sources_succeeded": ["openalex"],
  "errors": {"crossref": "..."},
  "ranking": "relevance",
  "count": 10,
  "results": [
    {
      "sources": ["openalex"],
      "source_rank": {"openalex": 1},
      "title": "...",
      "authors": ["..."],
      "year": 2024,
      "venue": "...",
      "doi": "...",
      "arxiv_id": null,
      "pmid": null,
      "abstract": "...",
      "url": "...",
      "pdf_url": "...",
      "citation_count": 12
    }
  ]
}
```

- OpenAlex 记录会从 `locations`/`best_oa_location` 中提取 arXiv ID 和开放获取 PDF 链接；`10.48550/arXiv.*` DOI 也会解析成 arXiv ID，保证同一预印本跨源去重。
- Crossref 和 OpenAlex 的 `Review of: ...`、`peer-review`、`editorial` 记录默认过滤，避免书评/审稿记录混进论文候选。
- `--rank citations` 先获取 relevance candidate pool，再在本地按 citation_count 排序；不会用全局高引用列表替换检索结果。
- 脚本不下载 PDF；返回 `pdf_url` 或 landing page，由 harness 的网页/PDF 工具读取。
- 脚本不判断论文质量；筛选和 claim-level 证据提取由主代理按 reading 协议完成。
- 退出码：`0` 至少一个来源成功；`1` 所有来源失败；`2` 参数或输入错误。

## 没有脚本/没有网络时

- 使用 harness 自带的学术搜索、网页搜索、PDF 阅读工具或已安装连接器。
- 手工维护同样的候选表：title、authors、year、venue、DOI/ID、URL、source、为什么候选。
- 缺少真实记录时明确说缺口；不要用记忆补齐。