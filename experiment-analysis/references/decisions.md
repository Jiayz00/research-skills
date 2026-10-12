# 归因、诊断与决策（decisions）

## 四类结果

| 情况 | 判断 | 动作 |
| --- | --- | --- |
| 运行没有回答节点问题（崩溃、OOM、超时、缺依赖） | 工程失败 | repair：修复同一节点，重跑同一节点 |
| 运行回答了，但结果平庸/不确定 | 科学结果 | refill：启动本轮下一个候选，或补 seed |
| 运行回答了，且明确优于当前父节点 | 明确胜者 | promote：让它成为下一轮父节点 |
| 目标达成，或连续 ~3 次失败/回退 | 停止条件 | stop：写实验总结并收束 |
| 结果异常、需要外部方法/根因 | 分析不足 | 移交 optimization-advisor |

不要用“结果不好”当作 repair 的理由；只有“没有回答”才是 repair。

## 消融归因

- 消融一次只改变一个组件；如果一次改了多个，不能归因到单个组件。
- 检查 baseline 是否同一代码/数据/评测；不同则先修 setup。
- 看 effect size 和 interval，不只看向上/向下。
- 检查交互：两个组件单独都无效，但组合有效，说明存在 interaction；需要额外实验。
- 检查 confounder：数据泄漏、额外 compute、不同 seed 数、评测选择偏差。
- 如果没有隔离变量，结论最多是 correlation，不要写成 cause。

## 失败与回归诊断

按顺序：

1. **确认失败类型**：崩溃/OOM/超时/断言/NaN/评测错误/结果退步。
2. **定位最后一个已知良好状态**：commit、配置、数据、环境。
3. **对比变化**：diff 代码、配置、依赖、硬件、数据。
4. **最小复现**：在不修改 frozen 节点的前提下，用临时目录/小输入复现。
5. **区分工程与科学**：修复后重跑同一节点；不要把工程失败当负结果。
6. **记录**：错误、命令、环境、修复、结果；避免下次重复踩坑。

如果无法在合理时间内定位，停止猜测，明确列出缺口并请求用户或移交 `diagnosing-bugs`。

## Plateau 与优化建议

连续多轮 refill/小改动都没有提升时：

- 先确认不是统计噪声或评测问题；
- 再看是否所有候选都在同一个局部设计里；
- 把问题交给 `optimization-advisor`：附 `analysis.json`、代码/diff、日志和环境约束；
- advisor 负责查文献/社区方法并提出修改方案；
- 验证仍由 `experiment-workflow` 建分支、固定 run contract 执行。

## 决策记录

`analysis.json` 最小字段：

```json
{
  "experiment": "...",
  "baseline": "...",
  "decision": "repair|refill|promote|stop",
  "confidence": "low|medium|high",
  "evidence": ["run-id:line"],
  "warnings": ["..."],
  "next_actions": ["..."]
}
```

- `confidence` 反映证据强度和覆盖度，不是情绪。
- `evidence` 至少包含一个 run 和一条日志/指标位置。
- `next_actions` 要可执行：启动什么、测什么、成功标准是什么。
- 决策改变父节点或停止整棵树时，写清理由。

## 分析报告模板

```markdown
# <experiment> analysis

## 结论
- 一句话结论 + decision + confidence

## 证据
- run manifest 摘要
- 关键指标表（value | run | source | line/field）
- 差值/interval/seed 数

## 诊断
- 哪些假设被支持/否定
- 失败/异常/confounder

## 限制
- 单种子、缺失 run、跨环境、评测偏差

## 下一步
- repair/refill/promote/stop 具体动作
- 如果移交 advisor：写出需要它回答的问题
```

报告里的每个数字都要能追溯到 `analysis.json`、`summary.json`、原始日志或 metrics 文件。