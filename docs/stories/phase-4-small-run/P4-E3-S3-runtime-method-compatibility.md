# Story P4-E3-S3：兼容现有 runtime 方法：深挖和清洗

状态：待实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为现有 `apps/api` Agent 编排代码的维护者，我希望 `HttpAgentRuntime` 暴露与现有深挖和清洗 runtime 相容的方法，以便局部切换到 HTTP active_run 时不需要大改上层业务编排。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 为 `HttpAgentRuntime` 增加 `run_deep_enrichment`、`run_lead_cleanup` 等与现有调用方兼容的方法签名和返回结构。

**建议文件：**

- Modify: `apps/api/app/agents/http_runtime.py`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/agents/test_http_runtime_compatibility.py`

**验收标准：**

- `run_deep_enrichment` 可将现有输入转换为 `apps/agents` Deep Enrichment run 请求。
- `run_lead_cleanup` 可将现有输入转换为 `apps/agents` Lead Cleanup run 请求。
- 返回结构能被现有上层 service 消费。
- 兼容层不改变现有本地 runtime 的行为。

**非目标：**

- 不接入生产入口。
- 不实现 LangGraph Agent API。
- 不写业务 core 表。

## Codex 提示词

```text
请执行 P4-E3-S3：兼容现有 runtime 方法：run_deep_enrichment 和 run_lead_cleanup。
要求使用 TDD；只新增 HTTP runtime 兼容层；不得修改现有本地 runtime 语义；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 中现有 LLM Agent 保持不变。
- `apps/agents` 独立服务运行，通过 HTTP API 交互。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
