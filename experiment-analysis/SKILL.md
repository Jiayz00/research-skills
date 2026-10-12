---
name: experiment-analysis
description: 分析已有实验结果与运行证据：日志核验、多种子聚合、差值/不确定性、消融归因、失败/回归诊断，并给出 repair/refill/promote/stop 建议。适用于 run logs、metrics、结果表、消融/对比分析；实际运行实验用 experiment-workflow，根因与外部方法调研用 optimization-advisor，出版级绘图用 research-figures。
---

# 实验结果分析（experiment analysis）

分析不是把数字变成一段叙述，而是建立一条可回溯的证据链：每个结论都能回到 run、配置、提交、日志行和一组有不确定性的数值。

## 边界

- 用于分析**已经存在**的运行、日志、指标表、消融和对比结果。
- 实际启动/修改/复现实验：用 `experiment-workflow`。
- “为什么还不好、还有哪些方法、社区怎么做”：用 `optimization-advisor`。
- 出版级图表与视觉审计：用 `research-figures`；论文结果段：用 `research-paper`。
- 不用于非实验数据的通用数据分析，也不用于可复现 bug 的根因诊断（那类问题用 `diagnosing-bugs`）。

## 四类输入

1. **运行标识**：run_id、variant、branch、commit、seed、status。
2. **数值**：最终指标、周期性 metric、cost/时间、评测输出。
3. **环境与配置**：命令、config、依赖/硬件、数据版本。
4. **原始证据**：日志路径、stdout/stderr、曲线、失败栈、异常退出信息。

缺少其中任何一项时，先标注缺口；不要用“大概”“应该”补齐。

## 分析循环

1. **盘点（inventory）**：列出所有 runs，标出 completed、failed、timeout、OOM、duplicate、aborted 和 missing。确认哪些 run 真正回答了它要测的假设。
2. **核验（validate）**：对每个入选 run 确认变体/配置/提交/种子、终局指标、轨迹和日志行。不能从状态或记忆推断结果。
3. **归一（normalize）**：确认所有比较使用同一 metric、同一评测协议、同一环境和同一横轴；对齐 step/token/epoch；无法对齐的不要硬比。
4. **聚合（aggregate）**：多种子给 n、mean、SD 和 95% interval；单种子明确写 “single seed”；发散/离群点是结果的一部分，不要静默删除。
5. **比较（compare）**：主张差异时看 treatment − baseline 的差值及其 interval；不要用“两个区间重叠”推断“没有差异”，也不要只看最好的一个 seed。
6. **归因（attribute）**：消融一次只改变一个变量；检查数据、compute、超参、评测和实现是否成为 confounder。
7. **诊断（diagnose）**：把 failure 分成“运行没答上”（修复后重跑）和“答上了但结果不理想”（科学结果）；回归要区分真实退步和噪声。
8. **决策（decide）**：给出 `repair`、`refill`、`promote`、`stop` 之一，并写清证据、confidence 和下一步。
9. **写报告（write-up）**：输出可读分析、机器可读 summary 和 provenance；再做图或写论文。

## 统计政策

- 默认以效应量和 interval 为主，不把 p-value 当成唯一结论。
- `n < 3` 时只给 warning 和原始值，不假装有稳定区间。
- 多种子：报告均值、SD、95% interval、n；不要只报 best seed。
- 单种子：明确写 single seed；可以做定性观察，不能宣称稳健差异。
- 配对比较：同 seed 对齐时优先 paired；种子集不同则 unpaired。
- 离群/发散：先检查是否实现/硬件问题；作为科学结果时保留并解释，不要为了让图好看而删。
- 多重比较：扫描很多 variant 时，不要把偶然的最好结果当成确定发现。
- 相关不等于因果：只有隔离变量的实验才能支撑归因。

## 分析脚本

用 stdlib-only 脚本汇总 tidy 数据：

```sh
python <本技能目录>/scripts/analyze_runs.py \
  --input runs.csv \
  --group variant --value metric \
  --run-id run_id --seed seed \
  --baseline baseline \
  --format markdown --output artifacts/topic/analysis/summary.md
```

- 输入是 CSV 或 JSONL；至少包含 group/value；推荐包含 run_id、seed、step、cost、status。
- 输出组统计、baseline 差值区间、配对/非配对方法和 warnings；报告包含每组 run_ids/seeds provenance。
- 重复 `(group, run_id, seed)` 默认保留首次、其余标为 dropped；用 `--duplicate-policy first|keep|error` 显式选择行为。
- 脚本不判断科学结论；决策和叙述由你根据日志、代码和实验设计写出。
- 需要画曲线时加 `--step step`；脚本会按 step 聚合，输出可交给 `research-figures` 的 tidy 数据。

## 输出

- 默认写到仓库 convention；无约定时用 `artifacts/<topic>/analysis/`。
- `analysis.md`：人类可读结论、证据、限制、下一步。
- `summary.json`：脚本输出的组统计、比较和 warnings。
- `metrics.csv`：可选，整理后的 tidy 表格，供 `research-figures` 或独立复查使用。
- `analysis.json`：在 summary 之上加入你的决策：
  ```json
  {
    "experiment": "...",
    "baseline": "...",
    "decision": "repair|refill|promote|stop",
    "confidence": "low|medium|high",
    "evidence": ["run-id:line", "..."],
    "warnings": ["..."],
    "next_actions": ["..."]
  }
  ```
- 所有结论都引用具体 run 和日志/指标位置；报告里给出可点击或可复现的路径。

## Handoff

- 决策已明确、只是要把结果表达出来：交给 `research-figures` / `research-paper`。
- 即时 `repair/refill/promote/stop` 由本技能决定；外部方法支撑的 modification 由 `optimization-advisor` 决定。
- 问题是“为什么”“还有哪些方法”“如何进一步优化”，或连续多轮 plateau/regression：交给 `optimization-advisor`，并附 `analysis.json`、代码上下文和日志路径。
- 分析发现运行没有回答假设：回到 `experiment-workflow` 的 repair 流程，不把工程失败写进科学结论。
- 外部方法/文献需要支撑：通过 `literature-review` 检索，不要凭记忆补 citation。

## 深入

- 证据盘点、run manifest、日志核验：`references/evidence.md`
- 多种子、区间、差值、离群与多重比较：`references/statistics.md`
- 归因、失败/回归诊断、repair/refill/promote/stop 与报告模板：`references/decisions.md`