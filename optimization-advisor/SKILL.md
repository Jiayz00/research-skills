---
name: optimization-advisor
description: 结合实验结果、日志和代码做根因诊断，检索论文、官方文档、源码、issue/PR 与社区方法，输出排序后的修改/优化建议和验证计划。适用于“为什么效果不好”“怎么优化”“还有哪些方法”“社区怎么做”“下一轮该试什么”；单纯解释 run 用 experiment-analysis，单纯查论文用 literature-review，实际改代码/跑实验用 experiment-workflow。
---

# 优化顾问（optimization advisor）

把“结果不好”变成一组**有证据、可证伪、能验证**的修改方案。你不是在给灵感清单；你是在把观察到的症状连接到根因、外部方法和下一个实验。

## 边界

- 用于：结果 + 代码需要进一步解释、连续 plateau/regression、想知道文献或社区有没有更好做法、需要排序后的修改/优化建议。
- 单纯解释已有 run、做即时 `repair/refill/promote/stop`：用 `experiment-analysis`。本技能不替代即时四选一决策；它回答“下一步改什么、为什么”。
- 单纯找论文/综述：用 `literature-review`。
- 实际修改代码、建分支、跑实验：用 `experiment-workflow`。
- 可复现 bug/性能回退：用 `diagnosing-bugs`；接口/重构设计：用 `codebase-design`。
- 本技能只做**只读诊断 + 方案**；不直接改 tracked files，不安装依赖，不启动完整训练/评测。

## 输入

至少拿到：

1. `experiment-analysis` 的 `analysis.json` / `analysis.md`；
2. 相关 run 的日志、指标、配置、seed、环境和 commit；
3. 当前代码、diff、分支和相关模块；
4. 项目 README、run contract、评测协议和已知约束；
5. 用户目标：优化哪个 metric、不能牺牲什么、算力/时间/内存预算。

输入缺失时不要停摆，按缺口降级：

- **没有 git 历史/commit**：检查文件内容、目录结构、日志时间戳、依赖版本和产物；把 revision 标为 unknown，并把“补 provenance”作为 `measurement_fix` proposal。
- **没有 config/run manifest**：从命令行、日志 header、产物和代码默认值推断；无法推断时明确写缺口，先提 instrumentation/measurement proposal。
- **没有 `analysis.json`**：对可用日志/指标做最小汇总；证据不足时写进 `diagnoses`，不要跳过或编造统计。
- **没有 clean baseline**：先建立/恢复 baseline；缺 baseline 时只能输出 exploratory proposals，并降低 confidence。
- diagnosis 只记录 hypothesis/evidence/confidence；依赖关系写在 proposal 的 `depends_on` 里。

## 标准流程

### 1. 框定问题

写清 primary metric 与方向、baseline/current/target、硬约束（compute、延迟、内存、数据、许可、兼容性）、成功标准和停止条件。

### 2. 证据盘点

- 复用 `experiment-analysis` 的统计结论和 provenance；不要重新发明统计。
- 读代码路径、diff、配置和日志，确认症状发生在哪一层。
- 区分实现问题、评测问题、数据问题、方法问题、资源问题。
- 把“确定的事实”“合理推断”“未知”分开写。

### 3. 根因诊断

从七类中选最相关的 2–4 个 falsifiable hypotheses：数据、目标/损失、模型/结构、优化/调度、评估/指标、工程/性能、实验设计。每个写成：

```text
If <cause>, then <change> will produce <observable prediction>.
Evidence: <run/log/code ref>.
Test: <read-only diagnostic or planned experiment>.
Confidence: low/medium/high.
```

不能写出 prediction 的想法不是 hypothesis；不要进入 proposal。

### 4. 外部调研

- 科研方法/新颖性（架构、目标、训练方法、评测协议、数据方法）→ `literature-review`。
- 工程实现/性能/工具链 → 官方文档、源码、release notes、GitHub issue/PR、changelog；可用 `agent-reach`、GitHub CLI 或 harness 自带工具。
- 混合问题两边都查，再合并证据。
- 社区讨论/论坛/博客/社交媒体只用于生成假设；必须标注 Tier 3，不能单独支撑高优先级方案。
- 记录来源、版本、日期和适用条件；不伪造 citation、benchmark 或“社区普遍认为”。

### 5. 适用性审查

对每个候选方法检查任务/数据/评测匹配、compute/内存/延迟预算、框架/版本/硬件/许可、实现复杂度、维护成本、是否已被当前代码覆盖或明确排除。不匹配的放进 `rejected` 并写原因。

### 6. 提出方案

输出 2–5 个排序后的 proposals。每个 proposal 至少包含：

- `id`、`title`、`diagnosis_id`、`target_metric`、`proposal_type`（`measurement_fix|method_change|engineering|evaluation|data`）；
- `change_spec`：具体改哪些文件/配置/算法，不实际应用；
- `evidence`：own_run / paper / official_doc / source / issue / community，带引用；
- `expected_effect`：定性或引用真实外部区间，禁止编造“预计 +X%”；
- `cost`、`risk`、依赖和副作用；
- `depends_on`：必须先完成的 proposal/条件；测量/口径修复通常是 prerequisite；
- `validation_plan`：现有 run contract 的命令、成功标准、seed 数和 `power_rationale`、停止/kill criterion；
- `priority`、`status`。

一个 proposal 只改变一个被研究的变量；不能隔离变量的方案要拆开或显式标为 bundle。

### 7. 排序与移交

用分桶而不是假精确分数：

```text
priority = impact × evidence strength × applicability ÷ (cost × risk)
```

- impact = 对 primary metric 的潜在影响；evidence strength = Tier 1/2/3；applicability = 任务/预算/版本匹配；cost/risk = 实现、compute、回归和维护风险。
- **测量/评测/provenance 修复优先**：指标被截断、日志与代码不一致、baseline/provenance 缺失时，先提 `measurement_fix` 或 `evaluation` 修复；它可能不直接提升 metric，但会阻塞其他比较，应作为 high-priority prerequisite。
- 被 `depends_on` 阻塞的方案不能进入验证；先做依赖，再比较方法变更。
- 把优先级最高的 `proposed` 方案交给 `experiment-workflow` 建分支、固定 run contract、运行实验；结果回流 `experiment-analysis`，下一次 advisor pass 更新 proposal 状态。

## 证据层级

- **Tier 1**：自己的 run/log/code、可复现只读诊断、项目内已验证事实。
- **Tier 2**：论文/预印本、官方文档、源码、release notes、maintainer 参与的 issue/PR。
- **Tier 3**：论坛、博客、社交媒体、非权威社区讨论；只能生成假设，必须标注。
- 冲突时：Tier 1 决定自己系统的现状；Tier 2/3 提供外部方法；不要用社区说法覆盖自己的实验结果。

## 只读诊断边界

可以做：读代码/日志/diff/config，静态分析、类型/依赖检查、单元测试、microbenchmark、profiler、在仓库外临时目录做最小复现。允许写缓存/临时文件。

不可以做：修改 tracked files、安装/升级依赖、修改 frozen 节点或 run contract、启动完整训练/评测或大额集群任务。需要这些动作时，写进 proposal 的 validation plan，交给 `experiment-workflow`。

## 输出

- 默认写到仓库 convention；无约定时用 `artifacts/<topic>/advice/`。
- `optimization-report.md`：问题、证据、诊断、外部方法、排序方案、被拒绝方案、下一步。
- `proposals.json`：结构化方案账本；核心字段为 `problem`、`metric`、`constraints`、`diagnoses`、`proposals`、`rejected`、`recommended_next`。完整 schema、排序和报告模板见 `references/proposals.md`。
- 每个外部 claim 带来源；每个方案带 validation plan；每个 rejected 方案写原因；不在报告里放未验证的优化百分比。

## 深入

- 根因分类、hypothesis 格式、只读诊断：`references/diagnosis.md`
- 文献/工程/社区证据路由与适用性审查：`references/search-routing.md`
- proposal schema、排序、报告模板与 handoff：`references/proposals.md`