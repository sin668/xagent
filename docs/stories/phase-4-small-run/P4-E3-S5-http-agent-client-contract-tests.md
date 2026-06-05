# Story P4-E3-S5：HTTP Agent client contract tests

状态：待实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为跨服务调用的维护者，我希望用 contract tests 固化 `apps/api` 与 `apps/agents` 的 HTTP 协议，以便后续 LangGraph Agent 迭代不会破坏调用兼容性。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 建立 HTTP Agent client 契约测试，覆盖成功、失败、鉴权失败和超时。

**建议文件：**

- Create: `apps/api/tests/contracts/test_http_agent_client_contract.py`
- Create/Modify: `apps/api/tests/fixtures/`
- Modify: `apps/api/app/agents/http_runtime.py`

**验收标准：**

- contract tests 覆盖 2xx 成功 envelope。
- contract tests 覆盖 401 鉴权失败。
- contract tests 覆盖 4xx/5xx 业务或服务错误。
- contract tests 覆盖请求超时。
- 测试不得依赖真实外部 LLM 调用。

**非目标：**

- 不要求启动真实 `apps/agents` 服务。
- 不做端到端业务联调。
- 不扩大 Agent 迁移范围。

## Codex 提示词

```text
请执行 P4-E3-S5：HTTP Agent client contract tests。
要求使用 TDD；用 mock server 或等价方式覆盖成功、失败、鉴权失败、超时；不得发起真实 LLM 调用；完成后执行两轮独立评审。
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
