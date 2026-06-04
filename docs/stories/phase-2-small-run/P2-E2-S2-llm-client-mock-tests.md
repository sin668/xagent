# Story P2-E2-S2：实现统一 `LLMClient` 和 mock 测试

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E2

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现统一 `LLMClient` 和 mock 测试”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 提供业务服务统一调用 LLM 的适配层。

**Files:**

- Create: `apps/api/app/services/llm_client.py`
- Test: `apps/api/tests/test_llm_client.py`

**Codex 提示词：**

```text
请执行 P2-E2-S2：实现统一 LLMClient 和 mock 测试。

要求：
1. 使用 superpowers:test-driven-development。
2. 实现 LLMClient，提供 generate_json(task_type, system_prompt, user_prompt, output_schema)。
3. 返回 provider、model、base_url、latency_ms、token_usage、output_json、raw_response、error。
4. 使用 httpx 或项目已有 HTTP 客户端调用 OpenAI-compatible chat completions 接口。
5. 测试使用 mock，不要求真实 LLM key。
6. 不实现 fallback，不实现 prompt 入库。
7. 运行 pytest apps/api/tests/test_llm_client.py。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e2-s2-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- mock 成功响应可解析为 JSON。
- 网络失败能返回结构化错误。

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

- 新增 `apps/api/app/services/llm_client.py`。
- 实现统一 `LLMClient.generate_json(task_type, system_prompt, user_prompt, output_schema)`。
- `LLMClient` 使用 OpenAI-compatible `/chat/completions` 接口。
- 返回结构化 `LLMClientResult`：
  - `provider`
  - `model`
  - `base_url`
  - `latency_ms`
  - `token_usage`
  - `output_json`
  - `raw_response`
  - `error`
- 按任务类型选择模型：
  - `SOURCE_DISCOVERY` -> `LLM_SOURCE_DISCOVERY_MODEL`
  - `LEAD_EXTRACTION` -> `LLM_EXTRACTION_MODEL`
  - `LEAD_GRADING` -> `LLM_GRADING_MODEL`
  - 未知任务 -> `LLM_DEFAULT_MODEL`
- 新增 `apps/api/tests/test_llm_client.py`，使用 `httpx.MockTransport` 覆盖成功响应、任务模型选择、网络失败和缺少 API key。

未执行：

- 未实现 fallback。
- 未实现 prompt 入库。
- 未调用真实 LLM。
- 未实现 Source Discovery Agent。
- 未执行 P2-E2-S3 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_client.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.llm_client'
```

失败原因符合预期：`LLMClient` 尚未实现。

GREEN：

- 新增 `LLMClientResult`。
- 新增 `LLMClient`。
- 使用 `httpx.AsyncClient` 调用 OpenAI-compatible chat completions。
- 用 mock 测试验证成功 JSON 解析和结构化错误返回。

## 验证结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_client.py -q
```

结果：

```text
4 passed in 0.05s
```

回归测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_client.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
35 passed in 0.98s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/llm_client.py apps/api/tests/test_llm_client.py
```

结果：通过，退出码 0。

## 两轮独立评审记录

### 第一轮评审：Story 范围与接口契约

结论：通过。

发现项：

- `generate_json` 签名符合 Story 要求。
- 返回字段覆盖 provider、model、base_url、latency_ms、token_usage、output_json、raw_response、error。
- mock 成功响应可解析 JSON。
- 网络失败能返回 `network_error` 结构化错误。
- 缺少 API key 时不发起 HTTP 请求，并返回 `configuration_error`。
- 本 Story 未越界实现 fallback 或 prompt 入库。

修正结果：

- 无新增阻塞问题，无需修正。

### 第二轮评审：安全、测试证据与合规边界

结论：通过。

发现项：

- 目标测试 4 条通过，相关回归测试 35 条通过。
- Python 编译通过。
- 测试使用 `httpx.MockTransport`，未调用真实 LLM，也不需要真实 API key。
- `Authorization` header 仅用于请求发送，不进入 `LLMClientResult`，避免泄露密钥。
- 未触发自动社交私信、加好友、登录后批量采集、反爬规避或非公开数据抓取。

修正结果：

- 无新增实质阻塞问题，无需修正。
