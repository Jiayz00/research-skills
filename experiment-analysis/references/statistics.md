# 统计与不确定性（statistics）

## 先确认比较是合法的

在算任何统计量之前确认：

- 两个 variant 使用同一 metric、同一方向和同一评测协议；
- run command、环境和数据版本一致（除非实验变量就是其中之一）；
- 横轴对齐（step、epoch、token 或 compute）；
- 只改变了一个被研究的变量；
- baseline 和 treatment 的 seed 集合可比。

不满足时，把结果标为 exploratory，不要包装成确认性结论。

## 多种子聚合

默认报告：

- `n`：独立 seed 数；
- `mean`：种子均值；
- `sd`：样本标准差（n−1）；
- `95% interval`：均值的不确定区间；
- `min` / `max`：帮助发现发散或异常；
- `single seed`：n=1 时明确写出。

规则：

- 不要只报 best seed。
- 不要先挑 seed 再算均值。
- seed 数不同要写明；不要假装相同。
- n<3 时不宣称稳定差异；区间只能作为观察。
- 不同 seed 出现定性分歧（一个发散、其他正常）时，把分歧本身作为结果，不要用宽区间掩盖。

## 差值优先

主张“A 比 B 好”时，重点看：

```text
delta = mean(treatment) - mean(baseline)
```

以及 delta 的 95% interval。不要用两个各自 variant 的 interval 是否重叠来判断差异是否存在；重叠的 interval 与差值是否跨 0 不是同一个问题。

- 同 seed 对齐时优先 paired difference；种子集不同则 unpaired。
- 差值区间跨 0 时，诚实结论是“在当前 n 下检测不到稳定差异”，不是“两者相同”。
- 差值区间窄但效应很小，要讨论实际意义，不只看是否跨 0。
- 一次比较一个主要 metric；多个 metric 时说明哪些是 primary、哪些是 secondary。

## 离群、发散与失败

- 发散/NaN/OOM/超时：先判断是工程失败还是科学结果；工程失败不进入 performance 均值。
- 异常低/高的 seed：先检查日志和配置；确认有效后保留，不要为了让图好看删除。
- 如果删除任何 run，必须写原因、原始值和替代分析。
- 同一节点多次 repair：区分“修复后的有效 run”和“失败尝试”；不要把失败尝试混进最终均值。

## 多重比较与扫描

- 扫很多超参时，最好的那个往往包含选择偏差；需要独立 seed 或 held-out 评测确认。
- 不要对每个 variant 都做一次显著性检验然后只报告显著的那个。
- 如果只做探索性 sweep，写成 ranked observations，不要写成确认性因果结论。
- 多重比较需要校正或预注册 primary comparison；本技能默认不自动宣称显著性。

## 成本与效率

- 报告 metric 时同时记录 compute/时间/显存/成本；否则“更好”可能只是“更贵”。
- Pareto 比较时，不要先对每个方法取单点再比较；看整个前沿或不同预算下的曲线。
- 对相同 compute 的比较，明确是相同 step、相同 token 还是相同 wall-clock。

## 脚本输出

`scripts/analyze_runs.py` 会给出：

- 每组 n/mean/sd/sem/95% interval/min/max；
- 相对 baseline 的 delta 和 bootstrap interval；
- paired/unpaired 方法；
- single-seed、缺失、重复、非有限值和多个 step 的 warnings。

脚本不会替你决定 repair/refill/promote/stop，也不会自动做多重比较校正；这些由你结合实验设计和证据判断。