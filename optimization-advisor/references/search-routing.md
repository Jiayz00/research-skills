# 外部证据路由（search routing）

## 先分类问题

| 问题 | 主路由 | 次路由 |
| --- | --- | --- |
| 新方法/架构/目标函数/训练算法 | `literature-review` | 官方实现/source code |
| 评测协议/统计方法/实验设计 | `literature-review` | 项目内评测文档 |
| 性能/吞吐/内存/精度/并行 | 官方文档、源码、issue/PR | 论文（若涉及新算法） |
| 框架/依赖/版本/API | 官方文档、release notes、changelog | maintainer issue/PR |
| 工具链/部署/数据管线 | 官方文档、source code | 工程博客（标注） |
| 社区惯例/踩坑 | issue/PR、讨论区 | 论坛/博客/社交媒体（仅假设） |

- 科研方法优先论文/预印本，工程实现优先 primary source。
- 混合问题两边都查，但把证据按 Tier 分层，不要混成一个“大家都说”。
- 只有社区讨论支持时，proposal 的 priority 不能是 high，除非有 Tier 1/2 证据补强。

## 查询构造

先写问题，再写 query：

1. **本地症状**：指标、失败模式、误差类型、瓶颈、版本。
2. **技术名词**：方法名、组件名、API、错误消息、benchmark。
3. **约束词**：framework/version、hardware、budget、license。
4. **时间**：方法/issue 是否仍然有效；默认优先当前维护版本。
5. **验证词**：官方实现、reproduction、ablation、issue resolved。

不要猜缩写全称；把缩写原样搜索，确认后再扩展。错误消息要保留关键原文，但先 redact secrets。

## Tier 分级

- **Tier 1**：自己的 run/log/code + 可复现只读诊断。
- **Tier 2**：论文/预印本、官方文档、源码、release notes、maintainer 参与的 issue/PR。
- **Tier 3**：论坛、博客、社交媒体、非权威讨论。

规则：

- Tier 3 只能生成 hypothesis；不能单独支撑 high-priority proposal。
- Tier 2 要检查版本/日期/适用条件；旧 issue、未合并 PR、废弃 API 都要标注。
- Tier 1 决定“我的系统现在是什么样”；外部证据决定“别人怎么解决”。
- 冲突时呈现差异，不要只挑支持自己方案的来源。

## 论文检索

走 `literature-review`，至少记录：

- 标题、作者、年份、venue/版本、DOI/arXiv/PMID；
- 方法解决了什么问题，在什么设定/规模下验证；
- 与当前任务的差异：数据、模型、compute、评测；
- 原文中支撑该方法的图表/章节位置；
- 是否已有官方实现或复现。

不能只凭摘要推荐方法；claim-level 结论必须读原文。

## 工程/社区检索

优先顺序：

1. 官方文档 / API reference / migration guide；
2. 源码与测试；
3. release notes / changelog；
4. maintainer 参与的 issue/PR；
5. 其他 issue/PR/讨论；
6. 工程博客/论坛/社交媒体（标注 Tier 3）。

对 issue/PR 检查：

- 是否 open/closed/merged；
- 影响哪个版本；
- maintainer 是否确认；
- 是否有 reproduction；
- 是否已被后续版本修复或废弃；
- 是否存在 license/兼容性限制。

## 适用性审查

每个外部方法进入 proposal 前问：

- 任务相同吗？数据/规模/评测可比吗？
- compute/memory/latency 预算能承受吗？
- 依赖版本/硬件/许可兼容吗？
- 实现复杂度和维护成本是多少？
- 是否已经有本地实现或更简单的替代？
- 是否能用一个固定 run contract 验证？
- 失败时的回退路径是什么？

不匹配的放到 `rejected`，并写明具体原因。

## 引用与 provenance

- 记录 URL、标题、版本、访问日期、关键引文/片段。
- 不伪造论文、issue 编号、PR 状态或 benchmark 数字。
- 只引用你实际读过的页面/原文；搜索结果的 snippet 只能作为发现。
- 对每个 proposal 的外部证据给出 `type` 和 `ref`，便于复核。
- 社区说法写成“有用户报告/讨论”，不要写成“已被证明”。

## 避免 solution shopping

- 每个外部方法都要对应一个本地 hypothesis；不是“这个方法流行所以试试”。
- 先问“它解决的是不是我观察到的问题”，再问“它是否在相似约束下有效”。
- 优先可快速证伪、单变量、低成本的方案。
- 不把多个外部方法打包成一个 proposal；拆成独立变量。