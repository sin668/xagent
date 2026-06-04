# P2-E2-S3 执行结果：实现技术失败 fallback，schema/合规失败不 fallback

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E2-S3-llm-fallback-rules.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E2-S3，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/services/llm_fallback.py`。
- 创建 `apps/api/tests/test_llm_fallback.py`。
- 扩展 `apps/api/app/services/llm_client.py` 的技术错误分类。
- 实现 fallback 策略：只允许技术失败 fallback，不允许 schema、编造和风险阻断 fallback。
- fallback 结果保留 `primary_provider_error`、`fallback_provider` 和 `fallback_used`。

未执行：

- 未实现真实备用 Provider 的密钥配置。
- 未调用真实 LLM。
- 未实现 prompt 入库。
- 未实现 Source Discovery Agent。
- 未执行 P2-E2-S4 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/services/llm_fallback.py`
- `apps/api/app/services/llm_client.py`
- `apps/api/tests/test_llm_fallback.py`
- `docs/stories/phase-2-small-run/P2-E2-S3-llm-fallback-rules.md`
- `_bmad-output/implementation-artifacts/codex-p2-e2-s3-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.llm_fallback'
```

失败原因：fallback 模块尚未实现，符合当前 Story 的 RED 预期。

GREEN：

- 新增 `LLMFallbackPolicy`、`LLMFallbackService`、`LLMFallbackResult`。
- 用 mock provider 验证技术失败可 fallback。
- 用 mock provider 验证 schema 校验失败、疑似编造、Forbidden/High 风险阻断不可 fallback。
- 在 `LLMClient` 中补充 `timeout_error` 和 `rate_limit_error` 分类。

## 4. 验证命令与结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py -q
```

结果：

```text
9 passed in 0.07s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
40 passed in 0.99s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/llm_fallback.py apps/api/app/services/llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_client.py
```

结果：通过，退出码 0。

## 5. 验收结果

- 技术失败可 fallback：
  - `network_error`
  - `timeout_error`
  - `rate_limit_error`
- schema/合规失败不 fallback：
  - `schema_validation_error`
  - `suspected_fabrication`
  - `risk_blocked`
  - `forbidden_risk`
  - `high_risk_blocked`
- fallback 结果保留 `primary_provider_error` 和 `fallback_provider`。
- 测试使用 mock provider，不依赖真实备用 Provider key。

## 6. 风控结果

- 未调用真实 LLM。
- 未输出 API key 明文。
- schema、疑似编造、Forbidden/High 风险阻断不会 fallback，避免绕过人工复核和风控闸门。
- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- 未改变 High/Forbidden 风险边界。

## 7. 双轮评审记录

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
