# 运行：固定契约、并行与失败处理

## 运行契约

- **所有“算数”的运行走同一个入口**：项目约定的运行命令（脚本 + 配置）。不要在临时 shell 里裸跑训练/评测命令——那样既没有日志，测的也可能不是已提交的代码。
- **命令固定**：基线确定一次，之后绝不改动。节点之间的差异只来自提交进 Git 的代码与配置。
- **先提交，再运行**：运行只认已提交的代码。启动前 `git status --short` 必须干净，并记录 commit hash。
- **一次运行一份日志**：日志落盘到约定位置（`runs/<name>.log` 或仓库既有 convention，见 `evidence.md`）。
- 同一节点已有运行在飞时不要重复发起；确需并发时显式写下理由。

## Run manifest

每次运行登记以下字段（写进日志头部或运行台账）：

| 字段 | 内容 |
| --- | --- |
| `run_id` | 唯一运行标识 |
| `variant` | 本轮配置/方法名 |
| `branch` | Git 分支 |
| `commit` | 完整或短 commit hash |
| `seed` | 随机种子；没有就写 none |
| `command` | 实际执行的完整命令 |
| `config` | 生效配置路径/摘要 |
| `environment` | 机器/队列/镜像、驱动、关键依赖版本 |
| `log_path` | 日志文件路径 |
| `metrics_path` | 结构化指标文件路径（如果有） |
| `status` | pending/running/completed/failed/timeout/oom/aborted |
| `started_at` / `finished_at` | 时间 |
| `notes` | 数据变化、人为中断、异常 |

- run manifest 是 `experiment-analysis` 的输入；字段缺失会降低分析 confidence。
- 环境差异是“同样代码结果不同”的第一大来源；不要省略。

## 按“首个完成”驱动（tick 语义）

不要用“等整批跑完”的屏障。一个 tick = 等到**任意一个**运行结束 → 立刻交给 `experiment-analysis` 读取证据和给决策建议 → 决定 repair / refill / promote / stop → 再等下一个。

按环境选等待机制：

- 本地：`wait -n`、进程监视，或每 10–30 秒轮询一遍运行表。
- 集群/队列（Slurm、PBS 等）：轮询 `squeue`/`sacct`，或作业完成钩子。
- 云/API：轮询任务状态接口。

等待只是睡眠信号，不是事实来源：每次醒来后重扫运行表，把所有新结束的运行逐一核对。一次只用一个等待机制（等待或“跑完再回来”二选一，不要叠加）。

## 失败处理

- 先看失败原因：容量/排队类失败通常可重试；启动之后失败必须读日志。
- 失败不是新节点：修复同一节点、重跑同一节点（遵守 `tree.md` 里的修复上限）。
- 等待超时只意味着“还没有变化”，不代表运行失败。
- 失败 run 保留 manifest 和日志；不要覆盖成成功记录。

## 并行槽位与 sizing

- 先把可用算力（GPU / CPU 槽位）数清楚，用有用的运行把槽位填满；一个节点同时只跑一个运行。
- 先决定 CPU 还是 GPU：数据准备、评测、API 调用往往 CPU 更划算。
- 从**装得下模型和最小 batch 的最小配置**起步；真的 OOM 或慢到无望再升级，不要一上来就用最大卡。
- 超时时间只对确实长跑的任务调大。
- 并行运行的节点必须属于同一轮或互不干扰；不要让两个运行写同一个日志/产出目录。

## 环境记录

把环境事实写进日志或笔记：机器/队列/镜像、驱动或 CUDA 版本、关键依赖版本、随机种子、数据版本。跨环境比较时先确认差异，再交给 `experiment-analysis` 判断是否可比。

## Handoff

- 运行结束：把 run manifest + `log_path` 交给 `experiment-analysis`。
- 需要外部方法/根因：把 `analysis.json` + 代码/diff + 约束交给 `optimization-advisor`。
- 方案验证：advisor 的 `proposals.json` 只提供 `change_spec` 和 validation plan；分支、提交、运行仍由本技能执行。