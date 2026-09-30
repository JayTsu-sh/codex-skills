---
name: codex-agent-flow
description: Apply a token-efficiency workflow when the user asks to use agent-flow or reduce development-session context and tool overhead; also supports measuring its effects. Not a default workflow for every coding task.
---

# Codex agent flow

主 agent 只做 coordinator：界定任务、委派、跟踪和验收整合；worker 承担具体调研、实现、
测试和实质审查。此流程改变执行分工，不改变完成标准；仓库规则、用户授权和硬件安全优先。

## 执行

1. 明确交付与可观察验收标准，按仓库要求确认工作树、交接及安全规则。coordinator 仅做
   安全委派所需的启动检查，不自行探索实现、编辑、测试或实质审查。
2. 将已核实事实写成短简报：目标、准确目录/分支/提交、允许修改的文件、验收检查、依赖、
   授权/设备限制、返回格式与停止条件。告诉 worker 共享工作树，须保留他人改动。
   同一批文件的发现、状态核对、证据整理优先交给一个连贯 worker；独立复核只有在能
   提高可信度时才增加。独立任务分开所有权；有依赖的阶段顺序执行，无资源冲突才并行。
3. worker 返回结果、证据路径、检查退出状态和未决风险，避免整段日志。coordinator 等待
   原生完成通知，期间只协调或规划，不重复 worker 的读取和执行。缺证据时给原 worker
   定向 follow-up；跨阶段时用短状态记录负责人、任务、进度和产物位置。
4. 委派 worker 完成针对性及仓库必需检查；可由实施 worker 验证，风险值得时独立复核。
   冗长本地软件检查按 [运行器](references/local-checks.md) 使用 `scripts/run_check.py`。
   它只运行给定 argv，不选择测试、不证明任务已完成，也不得包裹硬件操作。
5. coordinator 对照验收、Git 状态、活动任务和 worker 证据交付。争议交定向复核，
   不自己重跑实现或测试。说明结果、证据及限制；软件验证与真实硬件验证分开报告。

客户端没有委派能力时，明确 coordinator-only 模式无法在本会话完成具体工作，说明可用的
委派客户端或独立 worker 会话路径；不静默退回主 agent 执行。此 skill 不授予额外的委派、
部署、远程或设备操作权限，不降低显式确认门槛，不改变硬件超时和安全停止流程。

## 控制输入与轮次

- 大日志、JSON/HTML、库存先由确定性脚本筛选、计数或汇总，返回必要片段与原始证据路径。
  同时限制行数和行长，外层输出预算须容纳内层总量；截断后只补缺段。
- 批量执行独立查询；依赖、变更、审批和自适应后续保持顺序。工具发现用窄查询，文档只取
  相关章节并保留来源/版本。会话内复用已读规则与已证实事实，额外 skill 只在适用时加载。
- 重试先说明新假设或新证据；连续无新增信息就换诊断方法或报告具体阻碍。已有设计足以
  满足验收时停止扩展比较，额外优化须与任务相关。
- 进展只报新发现；原始证据留在文件，稳定约束引用权威文档。测量放在任务完成边界，
  不在每次工具调用后审计 token。缺遥测不等于零消耗。

## 按需读取

只加载当前触发的参考；普通开发无需读完下表。

| 触发条件 | 参考 |
|---|---|
| 执行冗长本地软件检查 | [local-checks.md](references/local-checks.md)：日志、退出码、等待 |
| 统计已有会话用量 | [usage.md](references/usage.md)：`usage.py`、字段与完整性 |
| 设计或解释 A/B 对照 | [ab-evaluation.md](references/ab-evaluation.md)：基线、质量与归因 |
| 当前上下文增长、压缩或换会话 | [context-growth.md](references/context-growth.md)：诊断、检查点 |
| 长任务、跨 worker 接续或异步任务 | [long-sessions.md](references/long-sessions.md)：等待、handoff |
| 判断 CodeGraph 是否减少搜索成本 | [codegraph.md](references/codegraph.md)：适用条件与对照 |
| 选择/实验分阶段模型或 effort | [model-routing.md](references/model-routing.md)：显式配置与阶段边界 |

测量口径：worker 自身 usage 反映上下文隔离，不等于端到端节省。根会话报告包含记录到的
子代理，不能再累加子代理总量；按 [用量字段](references/usage.md) 核对实际模型/effort，
不以请求配置代替。
模型路由是独立实验；skill 本身不会静默切模型，受控流程 A/B 中保持模型/effort 一致。
