---
name: experiment-workflow
description: 用实验循环推进研究型目标：建立 baseline、把假设做成 Git 分支、固定 run contract、留下可核查证据，并按结果决定 repair/refill/promote/stop。跑对比实验、消融、调参、复现、AB 验证时使用；一次性脚本或普通工程任务不触发；已有结果分析用 experiment-analysis，根因/外部方法调研用 optimization-advisor。
---

# 实验循环（experiment loop）

把研究目标组织成一棵**实验树**：每个节点 = 一条 Git 分支 = 一次可测量的尝试。目标不是“多跑几次”，而是让每个结果都成为下一步的地基，整棵树**向下生长**。

## 全流程位置

```text
literature-review → experiment-workflow → experiment-analysis
                                      ↘ optimization-advisor ↗
                                      → research-figures → research-paper
```

- 设计本轮假设前，需要相关工作/方法证据：读 `literature-review`。
- 每次运行答上节点后：交给 `experiment-analysis` 核验证据、算不确定性和给即时决策。
- 连续 plateau/regression，或要问“还有哪些方法/社区怎么做”：读 `optimization-advisor`，让它输出排序后的修改方案。
- 出图读 `research-figures`；写论文读 `research-paper`。
- 无论谁给建议，分支、提交、运行和 frozen 状态都由本技能负责。

## 四条硬规则

1. **freeze（冻结）**：一旦某次运行**回答了**该节点的问题——拿到 baseline 值或假设结果，好、坏、nan 都算——该分支立即冻结，永久不得再改。想测新假设，从它拉 child。运行**没答上**（报错、崩溃、OOM、超时、依赖缺失）时节点仍是 provisional（临时）状态：就地修复、重跑同一节点，不拉新分支。
2. **run contract 固定**：同一条运行命令、同一套环境，贯穿所有节点。子节点原样继承父节点的运行命令，永不改动；也不要用环境变量前缀（`LR=3e-4 python train.py`）变花样。节点之间唯一允许的差异，是**提交进 Git 的代码与配置**。
3. **变量进代码**：超参、开关、实验差异全部写进代码或配置文件再 commit，不要靠命令行参数或环境变量扫参——否则各节点的结果不可比。
4. **树向下生长**：一轮 = 一个决策的并列选项（小扇形）→ 取该轮明确胜者 → 下一轮从胜者继续下钻。全挂在根上（flat fan）和一根单链（noodle）都是失败形态。

## 空项目起步

1. **先看外部/内部实现**：需要相关工作或方法证据时读 `literature-review`；优先复用论文作者代码、官方仓库、社区复现。先 `git clone`，在真实代码上工作，不从空白开始。
2. **确定唯一 run contract**：例如 `python train.py --config configs/base.yaml`。写进 README 或约定文件，作为全项目契约；它必须把终局指标、紧凑摘要和生效配置打印到 stdout。
3. **建立 baseline**：在根提交上跑一次，确认命令能跑通、拿到起始指标，然后冻结 baseline。
4. **登记 manifest**：run_id、variant、branch、commit、seed、command、config、log_path、environment、status；字段约定见 `references/runs.md`。

## 一轮循环

每个 tick 重复下列动作；不要等整轮跑完才开始分析。

1. **读现状**：读父节点的代码与配置，找到本轮决策相关的旋钮。
2. **形成一轮假设**：只选一个决策，列出 2–4 个并列选项。不同决策不混在同一轮。需要外部方法时先读 `optimization-advisor`。
3. **建分支**：以父节点为起点（第 1 轮 = 基线；之后 = 上一轮胜者），为每个选项建一条普通 Git 分支。默认命名 `exp/<slug>`，仓库已有 convention 时优先沿用。同一轮各分支互为 sibling，各自只做该选项对应的改动。
4. **提交改动**：`git status --short` 必须干净；运行只使用已提交的代码。
5. **启动运行**：按固定 run contract 跑所有就绪节点。并行度按可用资源决定；日志落盘到约定位置（见 `references/evidence.md`）。
6. **按“首个完成”驱动**：一次 tick 只等一个运行完成，立刻交给 `experiment-analysis` 读取证据并给出决策建议；再决定补位或停止——不要使用“等全部跑完”的屏障。
7. **做决策**：结合 analysis 的建议和实验设计，执行四选一。
8. **冻结节点全程不动**：promote 只移动“焦点父节点”，绝不重写已测过的节点。

## 每个运行完成后的四个动作

- **repair（修复）**：运行什么都没答上 → 修复该节点的分支，重跑同一节点。连续两次答不上，停下来问用户。
- **refill（补位）**：结果平庸或不确定 → 启动本轮排队中的下一个节点，或补 seed 保持节奏。
- **promote（晋级）**：出现明确胜者 → 让它成为下一轮的父节点；新假设叠在它上面下钻。
- **stop（停止）**：目标达成，或连续约 3 次失败/回退 → 停止并写实验总结。

## 证据、产出与 handoff

- 运行命令必须打印终局指标、紧凑摘要和实际生效的配置；日志落盘（如 `runs/<name>.log`）。细节见 `references/evidence.md`。
- 每个完成的 run 交给 `experiment-analysis`；不要在实验循环里凭状态或记忆下结论。
- 报告、图表、数据、模型等产出写入仓库既有约定目录（无约定则 `artifacts/`），按主题/交付物分文件夹，文件名描述性。
- 需要外部方法/根因诊断：把 `analysis.json`、代码/diff、日志和约束交给 `optimization-advisor`。
- 出图前先读 `research-figures`；写论文时读 `research-paper`。
- 收尾时把整棵树写成一份实验总结：每个节点一行——测了什么、状态、头条结果，并给出产出文件路径。

## 深入

- 树形、轮次、父节点选择、修复上限与停止条件：`references/tree.md`
- run manifest、并行槽位、失败处理与环境记录：`references/runs.md`
- 日志证据与产出组织：`references/evidence.md`
- 子代理委派：`references/delegation.md`