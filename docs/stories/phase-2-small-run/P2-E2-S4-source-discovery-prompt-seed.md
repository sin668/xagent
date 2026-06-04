# Story P2-E2-S4：Source Discovery prompt/schema 入库与默认版本管理

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E2

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“Source Discovery prompt/schema 入库与默认版本管理”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 创建 Source Discovery 默认 prompt 和 output schema 的入库服务。

**Files:**

- Create: `apps/api/app/services/llm_prompt_templates.py`
- Create: `apps/api/app/services/default_prompt_seed.py`
- Test: `apps/api/tests/test_llm_prompt_templates.py`

**Codex 提示词：**

```text
请执行 P2-E2-S4：Source Discovery prompt/schema 入库与默认版本管理。

要求：
1. 使用 superpowers:test-driven-development。
2. 创建 source_discovery_default prompt template，task_type=SOURCE_DISCOVERY，version=v1.0，status=active，is_default=true。
3. output_schema_json 必须覆盖 candidates 和 blocked_candidates。
4. 每条 candidate 必须要求 source_url、platform、risk_level、discovery_reason、evidence_note。
5. Prompt 明确不抽取客户、不触达、不生成私信、不绕过平台限制。
6. 运行 pytest apps/api/tests/test_llm_prompt_templates.py。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e2-s4-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 默认 prompt/schema 可入库。
- prompt 内容包含合规边界。

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

- 新增 `apps/api/app/services/default_prompt_seed.py`。
- 新增 `apps/api/tests/test_llm_prompt_templates.py`。
- 创建 `source_discovery_default` 默认 prompt template 构造逻辑：
  - `task_type=SOURCE_DISCOVERY`
  - `version=v1.0`
  - `status=active`
  - `is_default=true`
  - 默认 provider/model 来自调用参数。
- `output_schema_json` 覆盖：
  - `candidates`
  - `blocked_candidates`
- 每条 `candidate` 必填：
  - `source_url`
  - `platform`
  - `risk_level`
  - `discovery_reason`
  - `evidence_note`
- Prompt 明确合规边界：
  - 不抽取客户
  - 不自动触达
  - 不生成私信
  - 不绕过登录、验证码、反爬或平台限制
  - High 只进入人工复核
  - Forbidden 进入 `blocked_candidates`
- 实现幂等入库：重复 seed 不新增第二条 active default。
- 修正 `LLMPromptTemplate` 时间默认值为时区感知 UTC，避免入库测试触发 `datetime.utcnow()` 弃用警告。

未执行：

- 未实现 Prompt Template 查询 API。
- 未实现后台治理接口。
- 未实现 Source Discovery Agent。
- 未执行 P2-E2-S5 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.default_prompt_seed'
```

失败原因符合预期：默认 prompt seed 服务尚未实现。

GREEN：

- 新增 `SourceDiscoveryDefaultPromptSeed`。
- 新增默认 prompt/schema 构造。
- 新增真实 PostgreSQL session 入库与幂等 seed。
- 修正 `LLMPromptTemplate` 时间字段为 UTC aware。

## 验证结果

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

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_template_model.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py apps/api/tests/test_phase2_data_foundation.py -q
```

结果：

```text
30 passed in 1.98s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/default_prompt_seed.py apps/api/app/services/llm_prompt_templates.py apps/api/app/models/llm_prompt_template.py apps/api/tests/test_llm_prompt_templates.py
```

结果：通过，退出码 0。

真实 PostgreSQL 查询确认：

```text
source_discovery_default SOURCE_DISCOVERY v1.0 active True
count= 1
```

## 两轮独立评审记录

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
