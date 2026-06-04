# P2-E2-S4 执行结果：Source Discovery prompt/schema 入库与默认版本管理

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E2-S4-source-discovery-prompt-seed.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E2-S4，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/services/default_prompt_seed.py`。
- 创建 `apps/api/tests/test_llm_prompt_templates.py`。
- 创建 `source_discovery_default` 默认 prompt template 构造和入库服务。
- 实现默认版本 `v1.0`、`active`、`is_default=true`。
- 实现幂等 seed：重复执行不会新增第二条 active default。
- 修正 `LLMPromptTemplate` 时间默认值为时区感知 UTC。

未执行：

- 未实现 Prompt Template 查询 API。
- 未实现后台治理接口。
- 未实现 Source Discovery Agent。
- 未调用真实 LLM。
- 未执行 P2-E2-S5 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/services/default_prompt_seed.py`
- `apps/api/app/models/llm_prompt_template.py`
- `apps/api/tests/test_llm_prompt_templates.py`
- `docs/stories/phase-2-small-run/P2-E2-S4-source-discovery-prompt-seed.md`
- `_bmad-output/implementation-artifacts/codex-p2-e2-s4-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.default_prompt_seed'
```

失败原因：默认 prompt seed 服务尚未实现，符合当前 Story 的 RED 预期。

GREEN：

- 新增 `SourceDiscoveryDefaultPromptSeed`。
- 构造 `source_discovery_default` prompt/schema。
- 使用真实 PostgreSQL session 完成幂等入库验证。
- 修正 `LLMPromptTemplate` 的 UTC 时间默认值。

## 4. 验证命令与结果

沙箱内目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates.py -q
```

结果：

```text
3 passed, 1 failed
```

失败原因：沙箱内连接真实 PostgreSQL 被权限拦截。

```text
PermissionError: [Errno 1] Operation not permitted
```

沙箱外目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates.py -q
```

结果：

```text
4 passed in 0.84s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_template_model.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_phase2_data_foundation.py -q
```

结果：

```text
30 passed in 1.98s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/default_prompt_seed.py apps/api/app/services/llm_prompt_templates.py apps/api/app/models/llm_prompt_template.py apps/api/tests/test_llm_prompt_templates.py
```

结果：通过，退出码 0。

真实 PostgreSQL 查询确认：

```text
source_discovery_default SOURCE_DISCOVERY v1.0 active True
count= 1
```

## 5. 验收结果

- 默认 prompt/schema 可入库。
- 默认模板为：
  - `name=source_discovery_default`
  - `task_type=SOURCE_DISCOVERY`
  - `version=v1.0`
  - `status=active`
  - `is_default=true`
- `output_schema_json` 覆盖 `candidates` 和 `blocked_candidates`。
- 每条 candidate 必须要求 `source_url`、`platform`、`risk_level`、`discovery_reason`、`evidence_note`。
- Prompt 内容包含合规边界：不抽取客户、不触达、不生成私信、不绕过登录、验证码、反爬或平台限制。
- 真实 PostgreSQL 中 active default 唯一。

## 6. 风控结果

- 未调用真实 LLM。
- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- Prompt 明确 High 只进入人工复核、Forbidden 进入 `blocked_candidates`。
- 未改变 High/Forbidden 风险边界。

## 7. 双轮评审记录

### 第一轮评审：Story 范围与 prompt/schema 契约

结论：通过。

发现项：

- 默认模板名称、任务类型、版本、状态和默认标记符合 Story 要求。
- `output_schema_json` 同时包含 `candidates` 和 `blocked_candidates`。
- candidate 必填字段覆盖 `source_url`、`platform`、`risk_level`、`discovery_reason`、`evidence_note`。
- Prompt 明确不抽取客户、不触达、不生成私信、不绕过平台限制。
- 本 Story 未越界实现 API、后台治理接口或 Source Discovery Agent。

修正结果：

- 无新增阻塞问题，无需修正。

### 第二轮评审：入库、幂等、安全与测试证据

结论：通过。

发现项：

- 目标测试 4 条通过，相关回归测试 30 条通过。
- Python 编译通过。
- 真实 PostgreSQL 查询确认只有 1 条 `SOURCE_DISCOVERY` active default prompt。
- 幂等 seed 不会创建重复 active default。
- 已修正 `LLMPromptTemplate` 的 `datetime.utcnow()` 弃用警告。
- 未触发自动社交私信、加好友、登录后批量采集、反爬规避或非公开数据抓取。

修正结果：

- 已将 `LLMPromptTemplate.created_at/updated_at` 默认值调整为 `datetime.now(UTC)`。
