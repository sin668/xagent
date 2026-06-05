# Story P4-E1-S2：实现内部 API Key 鉴权

状态：待实现  
Sprint：Sprint 1  
优先级：P0  
Epic：P4-E1

## 用户故事

作为系统维护者，我希望 `apps/agents` 的 Agent Run API 需要内部 API Key，以便同机独立端口也具备基础服务边界保护。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 为 `apps/agents` 实现 `X-Agents-Api-Key` 校验依赖。

**建议文件：**

- Create/Modify: `apps/agents/app/settings.py`
- Create/Modify: `apps/agents/app/security.py`
- Modify: `apps/agents/app/main.py`
- Test: `apps/agents/tests/test_internal_api_key_auth.py`

**验收标准：**

- 缺少 `X-Agents-Api-Key` 的受保护请求返回 401。
- API Key 错误的受保护请求返回 401。
- API Key 正确的受保护请求可继续执行。
- `/health` 可保持无需鉴权或明确记录鉴权策略。

**非目标：**

- 不实现用户级 JWT。
- 不实现 RBAC。
- 不接入外部身份系统。

## Codex 提示词

```text
请执行 P4-E1-S2：实现 apps/agents 内部 API Key 鉴权。
要求使用 TDD；只实现内部服务鉴权；用户权限仍由 apps/api 控制；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/agents` 不暴露公网服务。
- `apps/agents` 不写 core 业务表。

