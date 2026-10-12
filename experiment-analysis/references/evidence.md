# 证据盘点（evidence）

## Run manifest

每次实验至少登记：

| 字段 | 含义 |
| --- | --- |
| `run_id` | 唯一运行标识 |
| `variant` / `group` | 被比较的配置或方法 |
| `branch` / `commit` | 代码版本 |
| `seed` | 随机种子；没有就明确写 none |
| `status` | completed / failed / timeout / oom / aborted |
| `command` | 固定 run contract 的实际命令 |
| `config` | 生效配置路径或摘要 |
| `log_path` | stdout/stderr 日志路径 |
| `metrics_path` | 结构化指标文件路径 |
| `environment` | 机器/镜像/依赖/硬件 |
| `started_at` / `finished_at` | 时间信息 |
| `notes` | 异常、人为中断、数据变化 |

如果仓库已有实验台账/数据库，沿用它的字段；不要为了本技能另造一份互相冲突的真相。

## 盘点步骤

1. 从 run command、CI、日志目录或已有台账列出全部 runs。
2. 标记 terminal 状态；把 failed/timeout/oom 与 completed 分开。
3. 找出 duplicate：同一 variant + seed + commit 的重复运行；不要静默平均。
4. 找出 missing：计划中的 seed/variant 没有结果。
5. 找出不完整：没有终局指标、日志截断、训练中途停止。
6. 对每个 run 记录“它试图回答什么假设”和“它是否真的回答了”。

## 核验清单

对每个要纳入分析的 run 检查：

- [ ] 日志能识别 variant 和生效配置；
- [ ] commit/分支与报告中的版本一致；
- [ ] 终局指标存在且单位/方向明确；
- [ ] 长跑的 metric 轨迹可恢复；
- [ ] 环境/硬件/依赖差异已记录；
- [ ] 引用的日志行确实包含对应输出；
- [ ] 失败/异常没有被当作缺失数据删除。

## 从日志提取证据

- 用 `rg -n 'metric|summary|eval|final' <log>` 定位候选行，再读上下文。
- 终局值优先从明确 summary block 读取；不要从训练中偶然的最低点推断最终性能。
- 轨迹要保留 step/epoch/token 轴；不要只留最后一行。
- 关键数字记录 `run_id:line` 或 metrics 文件位置。
- 日志只解释“发生了什么”；因果归因需要实验设计，不要从单条日志推断。

## 证据缺口

- 缺日志：说明无法核验，不要用运行状态或记忆补结论。
- 缺配置：只能做低 confidence 的观察，不能进入 promote 决策。
- 缺种子：按 single seed 处理，并写清楚。
- 缺环境：把跨环境比较降级为探索性。
- 缺 baseline：先回到 `experiment-workflow` 建立 baseline 或明确说明这是无 baseline 的内部观察。

## Provenance 输出

分析报告中的每个数字都带一种 provenance：

```text
value | run_id | source (log/metrics) | line/field | environment
```

没有 provenance 的数字不要进入结论表。