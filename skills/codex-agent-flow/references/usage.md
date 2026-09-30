# 会话用量统计

面向本地 Codex rollout；Python 3.10+。统计已有记录不需要另开模型调用。

在任务结束后，记录会话完整 UUID。交互客户端从会话信息获取；`codex exec --json`
会输出 `thread.started` 事件，可读取其中的 `thread_id`。保存默认会话日志，不使用
`--ephemeral`。JSON 事件文件方便拿 ID；统计器读取的是本机 sessions 下的 rollout，
不是直接把 exec 的事件流当成 rollout。

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-agent-flow/scripts/usage.py" \
  --session <完整会话UUID> --json /tmp/flow-A.json

python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-agent-flow/scripts/usage.py" \
  --session <另一会话UUID> --json /tmp/flow-B.json
```

可指定 `--sessions-dir`，默认 `$CODEX_HOME/sessions` 或 `~/.codex/sessions`。
可指定 `--since 2026-09-30T10:00:00+08:00 --until 2026-09-30T11:00:00+08:00`，
区间左闭右开，按响应记账时间选择，不按任务开始时间推算。多会话接力的任务需对每个
独立根会话分别统计并合计；不要再次叠加已包含在根报告内的子代理。

统计规则：

- 只汇总 `token_usage_record.usage`，每个 `response_id` 一次；不累加累计总数。
- 首个 session_meta 确定日志所有者；thread_spawn 父子关系用于纳入子代理。
  forked_from_id 本身不能证明是子代理。过滤 thread_id，避免继承历史被算两遍。
- 缓存输入包含在 input 内，推理包含在 output 内。报告分列；不再次相加。
- 缺少记录、冲突记录或未知必需字段会报错，避免产生看似精确的零值。
  可选字段缺失会警告，零填充值不代表实际未发生；有 warning 时先检查数据完整性。
- 本地未落盘、被删除、在远程运行的会话无法被完整统计。换版出现新 schema 时需调整。
  usage.py 不保证适用于所有 Codex 版本。
- `tool_calls_with_matching_turn` 是可关联的外层工具调用数，exec 内的多条命令不展开；
  response_span_seconds 是响应时间跨度，不能代替端到端任务耗时。
- 不输出“调研成本占比”等伪精确归因，也不套用上游 Claude 的价格或 TTL 权重。

根报告的 `by_thread[<worker UUID>]` 是 worker 自身用量；对 worker UUID 单独运行统计器
仍会纳入它记录到的后代，不能自动视为该 worker 独占用量。模型/effort 的实际分布见
`responses_by_model_effort`；未知或与目标不符时标记路由未验证。根总量用于端到端比较，
`by_thread` 用于观察隔离；多根接力才分别合计，已纳入的子代理不能重复加。

如需实验设计，读 [A/B 对照](ab-evaluation.md)；仅统计现有用量无需加载实验或模型文档。
