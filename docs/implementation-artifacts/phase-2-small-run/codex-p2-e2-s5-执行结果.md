# P2-E2-S5 执行结果：Prompt template 查询 API 和后台治理接口基础

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E2-S5-prompt-template-query-api.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E2-S5，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/api/llm_prompt_templates.py`。
- 注册 `/llm-prompt-templates` 路由。
- 扩展 `LLMPromptTemplateService` 查询能力。
- 扩展 `LLMPromptTemplateListResponse.total`。
- 创建 `apps/api/tests/test_llm_prompt_templates_api.py`。
- 提供只读查询接口：
  - `GET /llm-prompt-templates`
  - `GET /llm-prompt-templates/{template_id}`
- 支持按 `task_type`、`status`、`is_default` 筛选。

未执行：

- 未实现 prompt 创建、编辑、删除接口。
- 未实现普通运营编辑权限。
- 未实现后台前端页面。
- 未实现 Source Discovery Agent。
- 未执行 P2-E3-S1 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/api/llm_prompt_templates.py`
- `apps/api/app/main.py`
- `apps/api/app/services/llm_prompt_templates.py`
- `apps/api/app/schemas/llm_prompt_template.py`
- `apps/api/tests/test_llm_prompt_templates_api.py`
- `docs/stories/phase-2-small-run/P2-E2-S5-prompt-template-query-api.md`
- `_bmad-output/implementation-artifacts/codex-p2-e2-s5-执行结果.md`

## 3. TDD 记录

RED：

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates_api.py -q
```

先暴露测试夹具问题：`pytest-asyncio` 严格模式不接受普通 `pytest.fixture` 的 async autouse fixture。修正为同步 helper 后重新运行，得到有效 RED：

```text
4 failed, 1 passed
```

失败原因：

- `/llm-prompt-templates` 返回 404。
- `/llm-prompt-templates/{id}` 返回 404。
- OpenAPI 中不存在 prompt template 路由。

GREEN：

- 新增只读 API。
- 注册路由。
- 增加查询 service。
- 增加列表响应 `total`。

## 4. 验证命令与结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates_api.py -q
```

结果：

```text
5 passed in 3.86s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_template_model.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_phase2_data_foundation.py -q
```

结果：

```text
35 passed in 4.28s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/api/llm_prompt_templates.py apps/api/app/services/llm_prompt_templates.py apps/api/app/schemas/llm_prompt_template.py apps/api/app/main.py apps/api/tests/test_llm_prompt_templates_api.py
```

结果：通过，退出码 0。

OpenAPI 方法验证：

```text
/llm-prompt-templates ['get']
/llm-prompt-templates/{template_id} ['get']
```

## 5. 验收结果

- 后台可查询 prompt template。
- 列表接口支持 `task_type`、`status`、`is_default` 筛选。
- 详情接口可查询 prompt 原文、schema、版本和状态。
- API 不返回 API key 或密钥字段。
- 第二阶段只读，不存在编辑 prompt 的普通接口。

## 6. 风控结果

- 未调用真实 LLM。
- 未输出 API key 明文。
- 未开放 prompt 编辑接口。
- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- 未改变 High/Forbidden 风险边界。

## 7. 双轮评审记录

### 第一轮评审：Story 范围与 API 契约

结论：通过。

发现项：

- `GET /llm-prompt-templates` 已实现。
- `GET /llm-prompt-templates/{id}` 已实现。
- 列表接口支持 `task_type`、`status`、`is_default` 筛选。
- 详情接口返回 prompt、schema、版本、状态等后台治理需要的信息。
- API 未返回 API key 或密钥字段。
- 本 Story 未越界实现编辑、删除、后台页面或 Source Discovery Agent。

修正结果：

- 已修正测试夹具实现，使 RED 能真实反映 API 缺口，而不是 pytest async fixture 兼容问题。

### 第二轮评审：只读治理、安全与测试证据

结论：通过。

发现项：

- 目标测试 5 条通过，相关回归测试 35 条通过。
- Python 编译通过。
- OpenAPI 确认 `/llm-prompt-templates` 与 `/llm-prompt-templates/{template_id}` 仅暴露 GET。
- 不存在普通运营编辑 prompt 的 POST/PUT/PATCH/DELETE 接口。
- 未触发自动社交私信、加好友、登录后批量采集、反爬规避或非公开数据抓取。

修正结果：

- 无新增实质阻塞问题，无需修正。
