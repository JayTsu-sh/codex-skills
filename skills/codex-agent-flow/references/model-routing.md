# 可选的分阶段模型路由

可以让不同阶段用不同模型，但切换方式取决于 Codex 的运行形式：

- **交互式 Codex TUI**：`/model` 切换当前聊天的模型，`/status` 检查当前选择。
- **独立的 headless 阶段**：`codex exec -m <model> -c 'model_reasoning_effort="low"'`
  可为该次调用指定模型。外层脚本可以在测试完成后启动一个独立的摘要/核对过程，只传入
  diff、清单和有界日志摘要。这样会新开上下文；构建简报、规则和证据的输入成本可能抵消
  较低的模型调用成本。必须检查真实退出码，完整日志仍留存，注明这是独立会话。
- **子代理**：仅在启用了多代理且当前任务允许委派时使用；如果 harness 提供逐代理模型
  选项，可给这个子代理指定模型。委派会增加上下文和协调；不能只为了让模型复述 Cargo
  通过与否而多开代理，测试运行器已经给出了该证据。

建议作为待验证的路由起点：

| 阶段 | 初始选项 | 理由 |
|---|---|---|
| 不确定的领域调研、架构、复杂实现 | GPT-6 Astra，当前有效推理档位 | 需要处理歧义与广泛推理 |
| 格式、构建、单测、Clippy | 本地确定性工具 | 这些检查不需要模型 |
| 摘要测试日志；将明确的清单项映射到测试证据 | GPT-6 Luna，low，且任务范围足够窄时 | 重复、边界清楚 |
| 失败原因不明；SCSI/LTFS 安全和协议判断；最终风险决定 | GPT-6 Astra | 低成本摘要不能代替正确性判断 |

上表是 2026-09-30 的实验起点，不是固定路由或性能结论；模型可用性与
使用额度依 Codex 产品和版本而变，应检查本机模型列表。参见[模型选择指南](https://developers.openai.com/api/docs/guides/model-selection)
和 [Codex 模型控制](https://learn.chatgpt.com/docs/developer-commands)。API 的按 token
价格不能推断 ChatGPT 订阅额度；使用本地记录字段或账号提供的额度指标。不能因为用了
Luna 就断言更省。

单独运行一次 Codex CLI 的例子：

```bash
codex exec -C /absolute/path/to/repo -m gpt-6-luna \
  -c 'model_reasoning_effort="low"' --sandbox read-only --json \
  -o /tmp/check-summary.txt - < /tmp/check-summary-prompt.txt \
  > /tmp/check-summary-events.jsonl
```

简报应保持精简，注明 base/head commit、已经执行的检查、相关 diff 路径、受限日志片段、
核对标准和该模型不能判断的范围。核对者只报告哪些标准有证据、哪些仍不确定；不能把退出码、
缺失日志、被忽略的测试或模拟验证结果升级成通过。由项目维护者或较强模型判断证据是否
满足原始验收。对 tape-rs，摘要模型不能替代 Holo 实验室或真实硬件验证，也不能从孤立的
日志片段推断 T10 协议语义。

把分阶段路由设为单独实验：A 组全程 Astra；B 组由 Astra 调研和实现，Luna 只做有限定的
日志摘要或清单核对。固定模型版本、推理档位、检查、证据材料、工具和阈值。按阶段记录
所有可用的 input/output/cache/reasoning 字段、两边会话调用、总响应数、耗时、返工和验收
结果。低模型可能降低 token 单价，但增加重试或漏项。只有验收相同且每个通过任务的实际
用量或费用下降时才保留该路由。

未指定子代理模型时的继承规则，以及逐代理 override 与 context fork 是否兼容，以当前
harness/schema 为准。只在用户/适用规则授权且工具允许时指定。
只有外层 runner 实际选模型才称自动路由。coordinator 若只整合，可单独实验较轻模型，
但协议、安全、验收争议必须由胜任的 worker 判断；不因主 agent 未改代码降低质量门槛。

实际路由的核对字段与统计方法见 [usage.md](usage.md)，实验控制见
[ab-evaluation.md](ab-evaluation.md)。handoff 和重载上下文成本均计入，不确定时升级处理。
