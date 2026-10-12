# 根因诊断（diagnosis）

## 证据盘点

先建立事实层：

```text
goal + metric
baseline + best result + gap
run ids + status + seed count
code revision + config diff + data version
environment + compute budget
known failures + constraints
```

- 复用 `experiment-analysis` 的结论；不要重新算一遍或另选一套口径。
- 把症状写成可观察事实：“validation AUC 在第 3k step 后停滞，5 seeds 均值 0.71，baseline 0.74”，而不是“模型不行”。
- 记录缺失信息；缺失会降低 hypothesis 的 confidence。

## 输入缺失时的降级

- 没有 git 历史：记录目录内容、文件 mtime、日志 header、依赖版本；把 revision 标为 unknown；先提“补 provenance/run manifest”的 measurement_fix。
- 没有 config：从命令行、日志、代码默认值和产物反推；反推不出就不要假设，写进证据缺口。
- 没有 analysis.json：对可用指标/日志做最小汇总；如果样本不足，降低 confidence 并提 instrumentation proposal。
- 没有 baseline：先建立或恢复 baseline；在此之前所有比较都标 exploratory。
- 日志与代码不一致：先复跑最小命令并对比 summary；测量修复优先于任何调参/方法比较。
- 输入缺失不阻塞诊断；它只改变 proposal 的优先级、confidence 和 `depends_on`。

## 七类根因

| 类别 | 常见症状 | 诊断问题 |
| --- | --- | --- |
| 数据 | 训练好/验证差、分布漂移、标签噪声、泄漏 | 数据覆盖是否匹配目标？train/eval 是否有重叠？预处理是否一致？ |
| 目标/损失 | 指标不升、优化目标错配、正则过强/过弱 | loss 是否真的对应 primary metric？辅助损失权重是否压过主目标？ |
| 模型/结构 | 容量不足、归纳偏置不匹配、组件缺失 | baseline 是否同容量？瓶颈在表示、注意力、归一化还是输出层？ |
| 优化/调度 | 不收敛、后期退化、对 lr/batch 敏感 | lr/warmup/schedule/optimizer/init 是否合理？梯度是否爆炸/消失？ |
| 评估/指标 | 离线好/线上差、指标虚高 | 评测协议是否公平？是否有选择偏差、泄漏、评测集污染？ |
| 工程/性能 | 慢、OOM、吞吐低、数值不稳 | 瓶颈在 compute、memory、数据加载、通信还是精度？ |
| 实验设计 | 结论不稳、无法归因 | 是否一次改变多个变量？seed 是否足够？baseline 是否同一环境和数据？ |

## Hypothesis 格式

生成 2–4 个 ranked hypotheses。每个必须 falsifiable：

```text
If <cause>, then <change> will make <observable metric> <direction> by <validation signal>.
Evidence: <run/log/code reference>.
Test: <read-only diagnostic or planned experiment>.
Confidence: low/medium/high.
```

示例：

```text
If the learning-rate warmup is too short, then extending warmup from 500 to 2k steps
will reduce early divergence and improve final validation loss at 3 seeds.
Evidence: 4 diverged runs all fail between step 120-300; config shows warmup=500.
Test: read-only profile of grad norm is possible; full test needs a fixed-contract run.
Confidence: medium.
```

不能写出预测和验证方式的，不要当成 hypothesis。

## 只读诊断配方

按成本从低到高：

1. **代码阅读**：数据流、loss、optimizer、eval、config 覆盖关系。
2. **diff 审查**：当前节点相对 parent 改了什么；是否意外改了多个变量。
3. **配置/依赖检查**：版本、flag、默认值、静默 fallback。
4. **日志/指标切片**：按 step、seed、variant 重排；找拐点、NaN、异常梯度。
5. **单元测试/小型 sanity check**：只验证局部行为，不改 tracked files。
6. **microbenchmark/profiler**：确认吞吐、内存、数据加载或 kernel 瓶颈。
7. **最小复现**：在 temp 目录复现一个局部现象，不碰主分支。

每个诊断记录：命令、环境、输入、输出、是否写入缓存、结论。不要把“跑起来了”当成证据。

## 常见模式

- **plateau**：先确认不是 seed 噪声/评测瓶颈，再判断容量、数据、目标或优化。
- **train/val gap**：数据泄漏、正则、容量、早停或分布差异。
- **high variance**：seed 不足、初始化/lr 敏感、数据顺序、硬件非确定性。
- **regression**：对比 parent diff，检查变量隔离、默认值变化、依赖升级。
- **OOM/吞吐**：先测瓶颈位置，再考虑精度、batch、并行、缓存、算子替换。
- **metric/eval mismatch**：检查评测脚本、采样、后处理、阈值选择和 test 集使用。

## 输出诊断条目

```json
{
  "id": "d1",
  "hypothesis": "...",
  "prediction": "...",
  "evidence": ["run-id:line", "code:path:Lx-Ly"],
  "test": "...",
  "confidence": "low|medium|high"
}
```

诊断不是结论；它必须连接到 proposal 和 validation plan。