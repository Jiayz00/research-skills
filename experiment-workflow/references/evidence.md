# 证据：运行日志与产出组织

运行日志是证据通道。判断结果、写报告、画图之前先读日志，不要凭记忆或运行状态推断。**证据采集**由本文件负责；**统计解释与科学决策**交给 `experiment-analysis`。

## 让运行自己打印证据

- 运行结束前打印**终局指标 + 紧凑摘要块**（不是只在训练过程中零散打印）。
- 回显实际生效的配置（超参、数据、种子），让日志能自证是哪个 variant。
- 长跑周期性打印一行指标，保证轨迹可搜索、可用来画曲线。
- 记录 run_id、variant、branch、commit、seed、environment、command、start/end time。
- 结果没进日志，就等于没发生——日志是事后证据的唯一入口。

## 日志约定

- 优先仓库既有 convention；无约定时使用 `runs/<name>.log`。
- 一次运行一份日志；不要在同一个文件里混多个 run。
- 终端 stream 和结构化 metrics 可以分开：stdout/stderr 给人类读，CSV/JSON 给分析脚本读。
- 日志里有秘密时先 redact；不要把 token、凭据、私有路径写进证据。
- 临时调试输出和正式 evidence 分开；正式 summary 放在 run 结束时。

## 读日志

- 用 `rg -n 'metric|summary|final|eval' <log>` 定位候选行，再读上下文。
- 引用具体行号或 metrics 字段支持结论。
- 截断的输出不等于“不存在”：一直搜/读到相关段落为止。
- 不要从运行状态或记忆推断结果。
- 日志只能说明“发生了什么”；因果和决策交给 `experiment-analysis`。

## 接受结论前的检查

- 日志能识别 variant 与生效配置；
- 终局指标与摘要存在；
- 长跑的轨迹可恢复；
- 引用的文件行确实包含对应输出；
- 失败/异常没有被当作缺失数据删除。

## 产出（reports / artifacts）

- 报告、图、CSV、PDF、模型等产出写入仓库既有约定目录；无约定则 `artifacts/`。
- 写之前先看已有目录结构，沿用其组织方式；按研究主题/交付物分文件夹，不要在根部堆文件。
- `figures/`、`data/`、`models/` 等子目录只在有用时建，不建空壳。
- 文件名要描述性（`patch-size.pdf`，不是 `fig1.pdf`）；把生成脚本放在产物旁边，保证可复现。
- 临时日志与草稿不要放进产出目录。
- 已发布的产物保持原路径；重排旧产物只在被要求时做，并同步更新引用。
- 报告内用相对链接引用图（`![Patch size](figures/patch-size.svg)`）；交付时给出完整路径。
- 出图前先读 `research-figures`；报告中引用运行数字时先经过 `experiment-analysis` 的证据核验。

## 与分析技能的边界

本技能只保证证据被打印、保存、可追溯。以下内容不在本文件里做：

- 多种子聚合、置信区间、差值比较；
- 离群/发散归因；
- repair/refill/promote/stop 的最终判断；
- 外部方法调研和优化建议。

这些由 `experiment-analysis` 和 `optimization-advisor` 负责；把 run manifest、日志路径和分析数据一起交给它们。