# P2-E2-S1 执行结果：扩展 LLM 配置和 Provider 健康检查

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E2-S1-llm-settings-health-api.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E2-S1，不执行下一个 Story。

已完成：

- 扩展 `apps/api/app/settings.py` 的 LLM 配置字段。
- 新增 `apps/api/app/api/llm_health.py`。
- 在 `apps/api/app/main.py` 注册 `/llm-health`。
- 新增 `apps/api/tests/test_llm_settings.py`。
- 新增 `apps/api/tests/test_llm_health_api.py`。
- 修正 `apps/api/.env` 中第二阶段 LLM 配置结构。

未执行：

- 未实现 `LLMClient`。
- 未调用真实 LLM Provider。
- 未实现多 Provider fallback。
- 未实现 prompt template API。
- 未实现 Source Discovery Agent。
- 未执行 P2-E2-S2 或其他后续 Story。

## 2. 修改文件

- `apps/api/.env`
- `apps/api/app/settings.py`
- `apps/api/app/api/llm_health.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_llm_settings.py`
- `apps/api/tests/test_llm_health_api.py`
- `docs/stories/phase-2-small-run/P2-E2-S1-llm-settings-health-api.md`
- `_bmad-output/implementation-artifacts/codex-p2-e2-s1-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py -q
```

结果：

```text
5 failed
```

失败原因：

- `Settings` 尚无 `llm_provider`、`llm_base_url`、`llm_source_discovery_model` 等字段。
- `/llm-health` 尚未注册，返回 404。

GREEN：

- 新增 LLM 配置字段：
  - `llm_provider`
  - `llm_api_key`
  - `llm_base_url`
  - `llm_default_model`
  - `llm_source_discovery_model`
  - `llm_extraction_model`
  - `llm_grading_model`
- 新增 `/llm-health` API。
- 注册路由。
- 修正 `.env` 的 LLM 配置结构。

## 4. 验证命令与结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py -q
```

结果：

```text
5 passed in 0.92s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
print(client.get('/llm-health').json())
PY
```

结果：

```text
{'provider': 'deepseek', 'models': {'default': 'deepseek-chat', 'source_discovery': 'deepseek-chat', 'extraction': 'deepseek-chat', 'grading': 'deepseek-chat'}, 'base_url_configured': True, 'api_key_configured': False, 'configuration_complete': False}
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_settings.py apps/api/tests/test_cors_api.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
34 passed in 0.98s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/settings.py apps/api/app/api/llm_health.py apps/api/app/main.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py
```

结果：通过，退出码 0。

## 5. 验收结果

- LLM 配置字段可从 `.env` 加载。
- 默认 Provider 为 `deepseek`。
- 默认模型为 `deepseek-chat`。
- `LLM_BASE_URL` 可配置，当前为 `https://api.deepseek.com/v1`。
- `/llm-health` 返回配置完整性、当前 provider、模型名、base URL 是否存在。
- `/llm-health` 不泄露 API key。
- 测试未调用真实 LLM。

## 6. 风控结果

- 未调用真实 LLM。
- 未输出 API key 明文。
- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- 未改变 High/Forbidden 风险边界。

## 7. 双轮评审记录

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
