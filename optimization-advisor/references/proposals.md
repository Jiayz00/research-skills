# 方案、排序与 handoff（proposals）

## Proposal 设计规则

每个 proposal 必须：

- 连接一个 `diagnosis_id`；
- 只改变一个被研究的变量；bundle 要显式标注并说明为什么不能拆；
- 有具体 `change_spec`：文件/配置/算法/依赖，不实际修改；
- 有 `proposal_type`：`measurement_fix`、`method_change`、`engineering`、`evaluation`、`data`；
- 有 `depends_on`：必须先完成的 proposal/条件；测量/口径修复通常是 prerequisite；
- 有外部/内部证据和 provenance；
- 有 `expected_effect`：定性或引用真实外部区间，禁止编造百分比；
- 有 `cost`、`risk`、依赖和副作用；
- 有 `validation_plan`：现有 run contract、成功标准、seed 数、`power_rationale`、停止/kill criterion；
- 能在固定 run contract 下验证；不要改变 baseline 的运行契约；
- 失败后能明确回退，不污染 frozen 节点。

## 排序

用高/中/低分桶，不写伪造的 0.87 分：

```text
priority = impact × evidence strength × applicability ÷ (cost × risk)
```

- **impact**：对 primary metric 的潜在影响。
- **evidence strength**：Tier 1 > Tier 2 > Tier 3；Tier 3 单独不支持 high。
- **applicability**：任务、数据、compute、版本、许可匹配。
- **cost**：实现时间、compute、依赖、维护。
- **risk**：回归、稳定性、数据/评测污染、不可逆改动。

排序后给 `recommended_next`，通常 1–3 个；不要把 5 个方案都说成“都值得做”。

## Proposal schema

```json
{
  "id": "p1",
  "title": "short actionable title",
  "diagnosis_id": "d1",
  "target_metric": "metric name and direction",
  "proposal_type": "measurement_fix|method_change|engineering|evaluation|data",
  "depends_on": [],
  "change_spec": "what to change, where, and why",
  "evidence": [
    {"type": "own_run|paper|official_doc|source|issue|community", "ref": "...", "note": "..."}
  ],
  "expected_effect": "qualitative or cited range",
  "cost": "low|medium|high",
  "risk": "low|medium|high",
  "validation_plan": {
    "command": "<project train/eval command>",
    "success_criteria": "...",
    "seeds": 3,
    "power_rationale": "exploratory; no power analysis, 3 seeds minimum",
    "stop_condition": "..."
  },
  "priority": "high|medium|low",
  "status": "proposed|accepted|running|supported|rejected|inconclusive|superseded",
  "experiment_ref": null
}
```

## 测量修复与前置依赖

- `measurement_fix`：修指标定义、日志、采样、unit、评测口径、provenance 或 baseline。它可能不直接提高 metric，但会阻塞其他方案；只要能证明它阻塞比较，就应排在 `method_change` 前。
- `depends_on`：数组，写 proposal id 或明确条件（如“clean baseline 已建立”“日志与代码复跑一致”）。
- 规则：
  - 不满足依赖的方案不能进入 `running`；
  - 依赖完成后重新审查方案的适用性，不自动沿用旧结论；
  - prerequisite 失败时，下游方案标为 `superseded` 或 `inconclusive`，不要假装可验证；
  - 报告里把 measurement/evaluation/provenance 修复和 method change 分开展示，避免把“修测量”和“真实优化”混为一谈。

## 统计功效与 seed 数

- `seeds` 是最小独立 seed 数，不是一个装饰字段。
- `power_rationale` 说明为什么这个数量足够做当前判断：有 power analysis/历史噪声估计就引用；没有就写 `exploratory; no power analysis`，并优先使用 3–5 seeds。
- 对高成本运行，写清预期可检测的最小效应、可接受的假阴性风险，或明确说明这是探索性筛选。
- n<3 的结果只能作为 exploratory；不要把它包装成确认性结论。

## 状态生命周期

- `proposed`：advisor 刚提出，尚未验证。
- `accepted`：用户/主代理决定验证；尚未开始。
- `running`：`experiment-workflow` 已建分支/发起 run。
- `supported`：新 run 的证据支持该方案。
- `rejected`：新 run 否定了方案，或适用性审查不通过。
- `inconclusive`：证据不足、confounder 太重或运行失败。
- `superseded`：被新的诊断/方案替代。

下一次 advisor pass 读取新的 `analysis.json` 和实验树状态，更新状态；不要重复提出已经有结论的方案。

## 报告模板

```markdown
# <topic> optimization advice

## 问题与约束
- primary metric:
- baseline/current/best:
- compute/latency/memory:
- success criteria:

## 证据摘要
- analysis.json:
- 关键 runs/logs:
- code/diff:
- 环境/版本:

## 诊断
| id | hypothesis | prediction | evidence | confidence |
| --- | --- | --- | --- | --- |

## 外部证据
### 学术方法
- <paper / version / relevance / evidence location>
### 工程/社区方法
- <official doc / source / issue / PR / community; tier>

## 推荐方案
| priority | id | title | type | target | depends_on | cost | risk | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### p1: <title>
- proposal_type:
- depends_on:
- diagnosis:
- change_spec:
- evidence:
- expected_effect:
- validation_plan (command, seeds, power_rationale, stop_condition):
- success/kill criteria:
- rollback:

## 被拒绝/证据不足
| title | reason | tier/gap |
| --- | --- | --- |

## 下一步
- recommended_next:
- handoff: experiment-workflow
- follow-up analysis: experiment-analysis
```

## Handoff contract

给 `experiment-workflow` 的 brief 包含：

- proposal id/title/change_spec；
- baseline/parent 节点和当前 frozen 状态；
- 固定 run contract；
- validation plan 的 success/kill criteria；
- 需要运行的 seeds 和预算；
- 回退方式；
- 允许/禁止修改的文件范围。

`experiment-workflow` 负责建分支、提交、启动运行；advisor 不直接改代码或跑完整实验。

## 结果回流

- `experiment-analysis` 产出新 `analysis.json`；
- advisor 读取新证据，更新 proposal 状态；
- 如果 supported，进入下一轮设计或 promote；
- 如果 rejected/inconclusive，记录原因，避免重复提案；
- 如果出现新 bottleneck，重新走 diagnosis，不沿用旧结论。

## 交付前检查

- [ ] 每个 proposal 有 diagnosis_id 和证据。
- [ ] 每个 proposal 只有一个被研究变量。
- [ ] expected_effect 没有伪造数字。
- [ ] validation_plan 使用固定 run contract。
- [ ] 有 success criteria 和 kill/stop condition。
- [ ] Tier 3 证据没有被当成 high-priority 的唯一支撑。
- [ ] rejected 方案有原因。
- [ ] `proposal_type`、`depends_on`、`power_rationale` 出现在 Markdown 报告中，不只留在 JSON。
- [ ] 没有修改 tracked files、安装依赖或启动完整训练。