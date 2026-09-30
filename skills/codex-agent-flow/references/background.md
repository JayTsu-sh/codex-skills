# 来源与历史证据

以下保留 2026-09-30 整理时的来源与样本；不是当前安装状态、当前工作树状态或新收益结论。

## 来源

上游 `git@gitlab.ln.ad:lisa/dev-plugins.git`，提交
`9d2b1107a8597a13d3819bb2bf43f6a3cd47d8fe`，目录 `plugins/agent-flow`。
[网页](http://gitlab.ln.ad/lisa/dev-plugins/-/tree/main/plugins/agent-flow)。当时通过已有 SSH
认证只读获取，未运行上游 hook/安装/远程任务。本 skill 是 Codex 实现，不是 Claude 兼容层。

保留了摘要日志、短交接、本地遥测；未移植 Claude hooks、TTL 变量、强制 clone、通过结果
自动缓存或通用远程 watchdog。仓库已有隔离、验证与硬件恢复要求优先；历史“默认单代理”
设计已由 SKILL.md 的 coordinator-only 流程取代。

资料：[Build skills](https://learn.chatgpt.com/docs/build-skills)、
[Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)、
[Testing Agent Skills](https://developers.openai.com/blog/eval-skills)。初版核对的本机 CLI 为
0.157.1；后续运行按当前 `--help` 和 schema 验证。

## 2026 年 9 月历史样本

- 09-14 至 09-27：20 份本地会话、4,368 次去重响应。input 564,565,700（cached
  549,159,168），output 2,478,249（reasoning 525,268）。缓存比例约 97.3%，平均 input
  约 129,250；子代理合计约占原始 token 的 8.1%。这是历史描述，不能预测新流程节省。
- 09-27 根会话 `01a0e058-b21e-7841-9a6f-3917b57645fa` 与两个子代理：1,632 次响应，
  input 219,639,298（cached 215,480,448），总 token 220,479,902，平均 input 约
  134,583。初版回放与独立统计一致、warnings 为空；不代表后来日志持续完整。
- 该根线程自身 1,600 次响应：四段 input 中位数 131,083 / 139,090 / 132,317 / 133,679，
  整体中位数 134,767，缓存比例 98.18%。样本较像固定高负担，未显示持续增长；不是当前
  `/status` 读数或未缓存计费输入，也不能代表其他会话。
- 该会话 1,563 次工具结果约 529 万字符，最大约 4 万，39 次超过 2 万。可用于定位大型
  读取/轮询，但字符数和工具关键词分类都不是精确 token 归因。

这些样本不证明 token、费用、额度或耗时改善。A/B 是否执行、质量是否一致及收益结论，
必须引用对应实验产物；旧版“本次未做 A/B”仅描述初版准备时点，不适用于后续实验。
历史六项 Python 测试和 frontmatter 校验记录也不替代当前验证；运行命令与结果由本次交付记录。

## 2026-09-30 单次隔离观察

同一脚本清单审计：主线程 `gpt-6-luna/medium` 一次 response 为 66,669 tokens；隔离
subagent `gpt-6-luna/low` 五次 response 为 31,980 tokens。两次 effort 和上下文不同，
且该比较未包含完整派发/汇总成本，只说明此样本 worker 自身输入负担较低；不能声称总体
节省 52%，也不能归因于模型或流程本身。这是非严格、方向性样本，后续结论需要受控对照。
