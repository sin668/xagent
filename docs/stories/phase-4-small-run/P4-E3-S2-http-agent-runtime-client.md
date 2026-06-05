# Story P4-E3-S2：实现 HttpAgentRuntime HTTP 调用客户端

状态：待实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为 `apps/api` 的 Agent 调用方，我希望有一个 `HttpAgentRuntime` 通过统一 envelope 调用 `apps/agents`，以便后续 active_run 和 shadow_run 都能走同一套服务间调用协议。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `apps/api` 中实现 HTTP Agent runtime client，负责鉴权 header、超时、错误映射和响应解析。

**建议文件：**

- Create: `apps/api/app/agents/http_runtime.py`
- Modify: `apps/api/app/agents/__init__.py`
- Test: `apps/api/tests/agents/test_http_agent_runtime.py`

**验收标准：**

- client 请求必须带 `X-Agents-Api-Key`。
- client 支持统一 request envelope 和 response envelope。
- 对 HTTP 401、4xx、5xx、timeout 有明确异常类型或错误返回。
- `apps/api` 不 import `apps/agents` 代码。
- 默认不替换现有本地 Agent runtime。

**非目标：**

- 不实现具体 Deep Enrichment 或 Lead Cleanup 方法适配。
- 不写入 `agent_task_runs`。
- 不实现结果轮询消费。

## Codex 提示词

```text
请执行 P4-E3-S2：实现 HttpAgentRuntime HTTP 调用客户端。
要求使用 TDD；覆盖成功、鉴权失败、服务错误和超时；不得 import apps/agents；完成后执行两轮独立评审。
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
