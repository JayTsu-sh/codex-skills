# 控制上下文增长

1. 在任务开始和有意义的边界用客户端 `/status` 看当前窗口，可用 `/statusline` 显示
   context stats；不每轮审计。当前窗口快照与累计 input 不同：高而稳定的每响应输入
   常是固定负担；持续增长需检查历史累积。先减少重复大文件、原始日志和重复计划。
2. 独立任务完成后保存短 handoff，再 `/new` 或新会话。未完任务剩余容量偏低时，先保存
   已验证检查点与活动任务，再 `/compact`；恢复后核对 Git、检查结果、活动任务和设备状态。
   state 文件本身不清空上下文，子代理也不会缩短主线程既有历史。
3. 可把剩余约 40% 准备检查点、约 25% 前压缩/换会话作为初始经验阈值，非产品默认或
   硬限制。以当前客户端的容量与自动压缩行为为准，运行中先到安全检查点；不可为 token
   目标中断设备操作、删除安全规则或省略验证。

压缩不删除 transcript，也不保证细节全保留，精确证据留在权威文件中。只有代表性会话表明
默认压缩影响工作、且受控试验有改善时才考虑调整 `model_auto_compact_token_limit`。
新会话需重载规则/状态；压缩可能改变 prompt prefix、降低下一响应缓存复用。比较总 input、
质量与重读成本，不只看缓存比例。尽量保持任务内规则/工具前缀稳定，但必须更新过期约束。

命令和配置依客户端/版本核对：[命令说明](https://learn.chatgpt.com/docs/developer-commands)、
[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。
[Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) 要求匹配的
prefix；API token rate limit 和价格不能推断 ChatGPT 订阅额度。
