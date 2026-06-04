# Story P2-E1-S1：创建 `llm_prompt_templates` 数据表、模型和 schema

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E1

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“创建 `llm_prompt_templates` 数据表、模型和 schema”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 建立 prompt/schema 入库管理基础，支持 Source Discovery、Lead Extraction、Lead Grading 的版本化 prompt。

**Files:**

- Create: `apps/api/alembic/versions/20260602_0020_create_llm_prompt_templates.py`
- Create: `apps/api/app/models/llm_prompt_template.py`
- Create: `apps/api/app/schemas/llm_prompt_template.py`
- Modify: `apps/api/app/models/__init__.py`
- Test: `apps/api/tests/test_llm_prompt_template_model.py`

**Codex 提示词：**

```text
请执行 P2-E1-S1：创建 llm_prompt_templates 数据表、模型和 schema。

要求：
1. 使用 superpowers:test-driven-development。
2. 创建 Alembic migration、SQLAlchemy model 和 Pydantic schema。
3. 字段包含 id、name、task_type、provider、model、system_prompt、user_prompt_template、output_schema_json、version、status、is_default、created_by、created_at、updated_at。
4. status 只允许 draft、active、paused、archived。
5. 同一 task_type 只允许一个 active + is_default=true 的模板，至少在 service/test 层表达约束。
6. 不实现 LLM 调用，不实现 Source Discovery Agent。
7. 运行 pytest apps/api/tests/test_llm_prompt_template_model.py。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e1-s1-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- migration 可创建 `llm_prompt_templates`。
- model/schema 字段完整。
- 状态枚举和默认模板约束有测试。

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

完成日期：2026-06-02

### 修改文件

- `apps/api/alembic/versions/20260602_0020_create_llm_prompt_templates.py`
- `apps/api/app/models/llm_prompt_template.py`
- `apps/api/app/schemas/llm_prompt_template.py`
- `apps/api/app/services/llm_prompt_templates.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/__init__.py`
- `apps/api/tests/test_llm_prompt_template_model.py`
- `_bmad-output/implementation-artifacts/codex-p2-e1-s1-执行结果.md`

### 验收结果

- 已创建 `llm_prompt_templates` Alembic migration，revision 为 `20260602_0020`，down_revision 为 `20260529_0019`。
- 已创建 `LLMPromptTemplate` SQLAlchemy model。
- 已创建 `LLMPromptTemplateCreate`、`LLMPromptTemplateUpdate`、`LLMPromptTemplateResponse`、`LLMPromptTemplateListResponse` Pydantic schema。
- 已新增 `LLMPromptTaskType` 和 `LLMPromptTemplateStatus` 枚举。
- 已通过 `LLMPromptTemplateService.validate_default_template_uniqueness` 在 service/test 层表达“同一 task_type 只能有一个 active 默认模板”的约束。
- 未实现 LLM 调用。
- 未实现 Source Discovery Agent。
- 未执行下一个 Story。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_prompt_template_model.py -q`：6 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/llm_prompt_template.py apps/api/app/schemas/llm_prompt_template.py apps/api/app/services/llm_prompt_templates.py apps/api/alembic/versions/20260602_0020_create_llm_prompt_templates.py apps/api/tests/test_llm_prompt_template_model.py`：通过。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0019:head --sql`：成功生成 PostgreSQL offline SQL，包含 `CREATE TABLE llm_prompt_templates`、状态枚举、任务类型枚举和 active 默认模板唯一索引。

### 风控结果

- 未新增自动社交私信、自动加好友、登录后批量采集或反爬规避能力。
- 未改变 High/Forbidden 风险边界。
- 未修改正式 `lead_sources` 或客户数据语义。
- 未使用内存 SQLite 作为正式验收依据。

### 双轮评审记录

#### 第一轮评审：Story 范围与需求一致性

结论：通过。

发现项：

- 实现范围限定在 `llm_prompt_templates` 数据表、模型、schema 和默认模板唯一性规则。
- 已覆盖 Story 要求的字段、状态枚举和 task_type。
- 未实现后续 LLM 调用、Prompt seed、API 或 Source Discovery Agent，未越过当前 Story 边界。

修正结果：

- 无需修正。

#### 第二轮评审：测试、迁移与合规边界

结论：通过。

发现项：

- 目标测试通过，新增 Python 文件编译通过。
- Alembic offline SQL 可生成 PostgreSQL DDL，迁移链 head 为 `20260602_0020`。
- 当前 Story 不涉及采集、抽取、触达或 High/Forbidden 消费，不引入合规风险动作。

修正结果：

- 无需修正。
