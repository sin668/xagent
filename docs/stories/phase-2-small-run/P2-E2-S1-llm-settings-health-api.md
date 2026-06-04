# Story P2-E2-S1：扩展 LLM 配置和 Provider 健康检查

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E2

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“扩展 LLM 配置和 Provider 健康检查”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 修正并扩展 LLM 配置，提供健康检查 API。

**Files:**

- Modify: `apps/api/app/settings.py`
- Create: `apps/api/app/api/llm_health.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_llm_settings.py`
- Test: `apps/api/tests/test_llm_health_api.py`

**Codex 提示词：**

```text
请执行 P2-E2-S1：扩展 LLM 配置和 Provider 健康检查。

要求：
1. 使用 superpowers:test-driven-development。
2. 新增 LLM_PROVIDER、LLM_API_KEY、LLM_BASE_URL、LLM_DEFAULT_MODEL、LLM_SOURCE_DISCOVERY_MODEL、LLM_EXTRACTION_MODEL、LLM_GRADING_MODEL。
3. 默认 Provider 为 deepseek，默认模型 deepseek-chat。
4. 健康检查 API 返回配置是否完整、当前 provider、模型名、base_url 是否存在。
5. 不在测试中调用真实 LLM。
6. 运行 pytest apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e2-s1-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- LLM 配置字段可从 `.env` 加载。
- health API 不泄露 API key。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动抽取。
- Forbidden 来源不得进入自动抽取。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。

## 实施结果

执行日期：2026-06-02

已完成：

- 扩展 `apps/api/app/settings.py`，新增第二阶段 LLM 配置字段：
  - `LLM_PROVIDER`
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_DEFAULT_MODEL`
  - `LLM_SOURCE_DISCOVERY_MODEL`
  - `LLM_EXTRACTION_MODEL`
  - `LLM_GRADING_MODEL`
- 默认 Provider 为 `deepseek`，默认模型为 `deepseek-chat`，默认 base URL 为 `https://api.deepseek.com/v1`。
- 修正 `apps/api/.env` 中 LLM 配置结构：
  - `LLM_PROVIDER=deepseek`
  - `LLM_BASE_URL=https://api.deepseek.com/v1`
  - 补齐 `LLM_SOURCE_DISCOVERY_MODEL=deepseek-chat`
  - 修正 `LLM_DEFAULT_MODEL=deepseek-chat`
  - `LLM_API_KEY` 留空，避免把 base URL 误当密钥。
- 新增 `apps/api/app/api/llm_health.py`。
- 在 `apps/api/app/main.py` 注册 `/llm-health` 路由。
- 新增 `apps/api/tests/test_llm_settings.py` 和 `apps/api/tests/test_llm_health_api.py`。
- 健康检查 API 只返回配置完整性、provider、模型名、base URL 是否存在、API key 是否存在，不返回 API key 明文，不调用真实 LLM。

未执行：

- 未实现 `LLMClient`。
- 未调用真实 LLM Provider。
- 未实现 fallback。
- 未实现 prompt template API。
- 未执行 P2-E2-S2 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py -q
```

结果：

```text
5 failed
```

失败原因符合预期：

- `Settings` 尚无 `llm_provider` 等 LLM 配置字段。
- `/llm-health` 尚未注册，返回 404。

GREEN：

- 新增 LLM 配置字段。
- 新增只读健康检查 API。
- 注册路由。
- 修正 `.env` 中与第二阶段设计不一致的 LLM 字段。

## 验证结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py -q
```

结果：

```text
5 passed in 0.92s
```

健康检查响应：

```text
{'provider': 'deepseek', 'models': {'default': 'deepseek-chat', 'source_discovery': 'deepseek-chat', 'extraction': 'deepseek-chat', 'grading': 'deepseek-chat'}, 'base_url_configured': True, 'api_key_configured': False, 'configuration_complete': False}
```

回归测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_settings.py apps/api/tests/test_cors_api.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
34 passed in 0.98s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/settings.py apps/api/app/api/llm_health.py apps/api/app/main.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py
```

结果：通过，退出码 0。

## 两轮独立评审记录

### 第一轮评审：需求覆盖与 Story 范围

结论：通过。

发现项：

- Story 要求的 7 个 LLM 配置字段均已实现。
- 默认 Provider 和模型符合第二阶段产品技术设计。
- `/llm-health` 已注册并进入 OpenAPI。
- 健康检查 API 不调用真实 LLM。
- 本 Story 未越界实现 `LLMClient`、fallback、prompt API 或 Agent 调度。

修正结果：

- 已修正 `apps/api/.env` 中原有 `LLM_PROVIDER=openai`、`LLM_API_KEY` 误填 base URL、`LLM_DEFAULT_MODEL=cdeepseek-chat` 和缺少 `LLM_SOURCE_DISCOVERY_MODEL` 的问题。

### 第二轮评审：安全、测试证据与合规边界

结论：通过。

发现项：

- 目标测试 5 条通过，相关回归测试 34 条通过。
- Python 编译通过。
- 健康检查响应未包含 `api_key` 字段，也不输出密钥值。
- `configuration_complete=False` 是当前 `.env` 中未配置真实 `LLM_API_KEY` 的正确结果，符合“不在测试中调用真实 LLM”的边界。
- 未触发自动社交私信、加好友、登录后批量采集、反爬规避或非公开数据抓取。

修正结果：

- 无新增实质阻塞问题，无需修正。
