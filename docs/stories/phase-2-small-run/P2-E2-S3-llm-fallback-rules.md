# Story P2-E2-S3：实现技术失败 fallback，schema/合规失败不 fallback

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E2

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现技术失败 fallback，schema/合规失败不 fallback”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 明确 fallback 只处理技术失败，不处理内容和合规失败。

**Files:**

- Modify: `apps/api/app/services/llm_client.py`
- Create: `apps/api/app/services/llm_fallback.py`
- Test: `apps/api/tests/test_llm_fallback.py`

**Codex 提示词：**

```text
请执行 P2-E2-S3：实现技术失败 fallback，schema/合规失败不 fallback。

要求：
1. 使用 superpowers:test-driven-development。
2. 技术失败包括网络、超时、限流。
3. schema 校验失败、疑似编造、Forbidden/High 风险阻断不得 fallback。
4. fallback 结果必须保留 primary_provider_error 和 fallback_provider。
5. 不实现真实备用 Provider 的密钥配置时，测试用 mock provider。
6. 运行 pytest apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e2-s3-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 技术失败可 fallback。
- schema/合规失败不 fallback。

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

- 新增 `apps/api/app/services/llm_fallback.py`。
- 新增 `apps/api/tests/test_llm_fallback.py`。
- 在 `apps/api/app/services/llm_client.py` 中补充技术失败错误分类：
  - HTTP 429 -> `rate_limit_error`
  - `httpx.TimeoutException` -> `timeout_error`
  - `httpx.RequestError` -> `network_error`
- 实现 `LLMFallbackPolicy.should_fallback`：
  - 允许 fallback：`network_error`、`timeout_error`、`rate_limit_error`
  - 禁止 fallback：`schema_validation_error`、`suspected_fabrication`、`risk_blocked`、`forbidden_risk`、`high_risk_blocked`
- 实现 `LLMFallbackService.generate_json_with_fallback`，支持 primary/fallback mock provider 编排。
- fallback 结果保留：
  - `primary_provider_error`
  - `fallback_provider`
  - `fallback_used`

未执行：

- 未实现真实备用 Provider 的密钥配置。
- 未调用真实 LLM。
- 未实现 prompt 入库。
- 未实现 Source Discovery Agent。
- 未执行 P2-E2-S4 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.llm_fallback'
```

失败原因符合预期：fallback 模块尚未实现。

GREEN：

- 新增 `LLMFallbackPolicy`、`LLMFallbackService`、`LLMFallbackResult`。
- 用 mock provider 验证技术失败可 fallback。
- 用 mock provider 验证 schema/编造/风险阻断不可 fallback。
- 补充 `LLMClient` 的超时和限流错误分类。

## 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py -q
```

结果：

```text
9 passed in 0.07s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
40 passed in 0.99s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/llm_fallback.py apps/api/app/services/llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py
```

结果：通过，退出码 0。

## 两轮独立评审记录

### 第一轮评审：Story 范围与 fallback 规则

结论：通过。

发现项：

- 技术失败 `network_error`、`timeout_error`、`rate_limit_error` 可 fallback。
- schema 校验失败、疑似编造、Forbidden/High 风险阻断不 fallback。
- fallback 成功结果保留 `primary_provider_error` 和 `fallback_provider`。
- primary 成功时不会调用 fallback。
- 本 Story 未越界实现真实备用 Provider 密钥配置、prompt 入库或 Agent。

修正结果：

- 无新增阻塞问题，无需修正。

### 第二轮评审：测试证据、安全与合规边界

结论：通过。

发现项：

- 目标测试 9 条通过，相关回归测试 40 条通过。
- Python 编译通过。
- 测试使用 mock provider，未调用真实 LLM，也不需要真实备用 Provider key。
- 合规风险类错误不会 fallback，避免绕过 Forbidden/High 风险闸门。
- 未触发自动社交私信、加好友、登录后批量采集、反爬规避或非公开数据抓取。

修正结果：

- 无新增实质阻塞问题，无需修正。
