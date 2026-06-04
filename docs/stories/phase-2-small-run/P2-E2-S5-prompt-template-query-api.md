# Story P2-E2-S5：Prompt template 查询 API 和后台治理接口基础

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E2

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“Prompt template 查询 API 和后台治理接口基础”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 提供 prompt template 只读查询接口，供后台治理页面使用。

**Files:**

- Create: `apps/api/app/api/llm_prompt_templates.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_llm_prompt_templates_api.py`

**Codex 提示词：**

```text
请执行 P2-E2-S5：Prompt template 查询 API 和后台治理接口基础。

要求：
1. 使用 superpowers:test-driven-development。
2. 提供 GET /llm-prompt-templates 和 GET /llm-prompt-templates/{id}。
3. 支持按 task_type、status、is_default 筛选。
4. 第二阶段只读，不开放普通运营编辑。
5. API 不返回敏感密钥。
6. 运行 pytest apps/api/tests/test_llm_prompt_templates_api.py。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e2-s5-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 后台可查询 prompt template。
- 不存在编辑 prompt 的普通接口。

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

- 新增 `apps/api/app/api/llm_prompt_templates.py`。
- 在 `apps/api/app/main.py` 注册 `/llm-prompt-templates` 路由。
- 扩展 `apps/api/app/services/llm_prompt_templates.py`：
  - `list_templates`
  - `get_template`
- 扩展 `LLMPromptTemplateListResponse`，增加 `total`。
- 新增 `apps/api/tests/test_llm_prompt_templates_api.py`。
- 提供只读接口：
  - `GET /llm-prompt-templates`
  - `GET /llm-prompt-templates/{template_id}`
- 支持筛选：
  - `task_type`
  - `status`
  - `is_default`
- OpenAPI 确认第二阶段只读，不暴露 POST/PUT/PATCH/DELETE。
- API 响应不返回 API key 或密钥字段。

未执行：

- 未实现 prompt 创建、编辑、删除接口。
- 未实现普通运营编辑权限。
- 未实现后台前端页面。
- 未实现 Source Discovery Agent。
- 未执行 P2-E3-S1 或其他后续 Story。

## TDD 记录

RED：

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates_api.py -q
```

先暴露测试夹具问题：`pytest-asyncio` 严格模式不接受普通 `pytest.fixture` 的 async autouse fixture。修正为同步 helper 后重新运行，得到有效 RED：

```text
4 failed, 1 passed
```

失败原因符合预期：

- `/llm-prompt-templates` 返回 404。
- `/llm-prompt-templates/{id}` 返回 404。
- OpenAPI 中不存在 prompt template 路由。

GREEN：

- 新增只读 API。
- 注册路由。
- 增加查询 service。
- 增加列表响应 `total`。

## 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates_api.py -q
```

结果：

```text
5 passed in 3.86s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_template_model.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_phase2_data_foundation.py -q
```

结果：

```text
35 passed in 4.28s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/api/llm_prompt_templates.py apps/api/app/services/llm_prompt_templates.py apps/api/app/schemas/llm_prompt_template.py apps/api/app/main.py apps/api/tests/test_llm_prompt_templates_api.py
```

结果：通过，退出码 0。

OpenAPI 方法验证：

```text
/llm-prompt-templates ['get']
/llm-prompt-templates/{template_id} ['get']
```

## 两轮独立评审记录

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
