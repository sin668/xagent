# Story P2-E1-S2：创建 `agent_task_runs` 数据表、模型和状态机 schema

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E1

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“创建 `agent_task_runs` 数据表、模型和状态机 schema”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 建立 Agent 任务运行审计事实表。

**Files:**

- Create: `apps/api/alembic/versions/20260602_0021_create_agent_task_runs.py`
- Create: `apps/api/app/models/agent_task_run.py`
- Create: `apps/api/app/schemas/agent_task_run.py`
- Create: `apps/api/app/services/agent_task_runs.py`
- Modify: `apps/api/app/models/__init__.py`
- Test: `apps/api/tests/test_agent_task_run_model.py`

**Codex 提示词：**

```text
请执行 P2-E1-S2：创建 agent_task_runs 数据表、模型和状态机 schema。

要求：
1. 使用 superpowers:test-driven-development。
2. 创建 agent_task_runs migration、model、schema 和基础 service。
3. 字段包含 task_type、status、trigger_source、input_json、output_summary_json、llm_provider、llm_model、prompt_template_id、prompt_version、token_usage_json、latency_ms、error_message、retry_count、started_at、finished_at、created_at、updated_at。
4. 状态机包含 pending、running、succeeded、failed、retry_pending、paused、cancelled、manual_review_required。
5. task_type 至少支持 SOURCE_DISCOVERY、LEAD_EXTRACTION、LEAD_GRADING、RETRY_WORKER。
6. 实现 start/succeed/fail/mark_retry_pending 的最小 service 方法并测试状态流转。
7. 运行 pytest apps/api/tests/test_agent_task_run_model.py。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e1-s2-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- `agent_task_runs` 可审计任务输入、输出、错误、模型和重试。
- 非法状态流转被测试覆盖。

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

- `apps/api/alembic/versions/20260602_0021_create_agent_task_runs.py`
- `apps/api/app/models/agent_task_run.py`
- `apps/api/app/schemas/agent_task_run.py`
- `apps/api/app/services/agent_task_runs.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/__init__.py`
- `apps/api/tests/test_agent_task_run_model.py`
- `_bmad-output/implementation-artifacts/codex-p2-e1-s2-执行结果.md`

### 验收结果

- 已创建 `agent_task_runs` Alembic migration，revision 为 `20260602_0021`，down_revision 为 `20260602_0020`。
- 已创建 `AgentTaskRun` SQLAlchemy model。
- 已创建 `AgentTaskRunCreate`、`AgentTaskRunUpdate`、`AgentTaskRunResponse`、`AgentTaskRunListResponse` Pydantic schema。
- 已新增 `AgentTaskType` 和 `AgentTaskRunStatus` 枚举。
- 已实现 `AgentTaskRunService.build_initial_payload`、`start`、`succeed`、`fail`、`mark_retry_pending`。
- 已覆盖非法状态流转和最大重试次数规则。
- 未执行下一个 Story。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q`：12 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/agent_task_run.py apps/api/app/schemas/agent_task_run.py apps/api/app/services/agent_task_runs.py apps/api/alembic/versions/20260602_0021_create_agent_task_runs.py apps/api/tests/test_agent_task_run_model.py`：通过。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260602_0021 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260602_0020:head --sql`：成功生成 PostgreSQL offline SQL，包含 `CREATE TABLE agent_task_runs`、任务类型枚举、状态枚举和 `prompt_template_id` 外键。

### 风控结果

- 未新增自动社交私信、自动加好友、登录后批量采集或反爬规避能力。
- 未改变 High/Forbidden 风险边界。
- 未实现 Agent 自动运行、LLM 调用或来源消费。
- 只建立任务运行审计事实表和状态机基础。

### 双轮评审记录

#### 第一轮评审：Story 范围与需求一致性

结论：通过。

发现项：

- 实现覆盖 Story 要求的 `agent_task_runs` 表、模型、schema、枚举和基础状态机 service。
- 字段覆盖 task_type、status、trigger_source、input/output JSON、LLM provider/model、prompt 引用、token、latency、error、retry 和时间字段。
- 未扩展到调度器、LLMClient、Source Discovery Agent 或 LEAD_EXTRACTION 消费，未越过当前 Story 边界。

修正结果：

- 已补充 `AgentTaskRun` 和新枚举到 `apps/api/app/models/__init__.py` 的实际导入和 `__all__`。

#### 第二轮评审：测试、迁移与合规边界

结论：通过。

发现项：

- 目标测试和上一个 Story 回归测试通过：12 passed。
- 新增 Python 文件编译通过。
- Alembic offline SQL 生成成功，迁移链 head 为 `20260602_0021`。
- 本 Story 仅涉及审计事实表和状态机基础，不引入采集、触达或 High/Forbidden 自动消费风险。

修正结果：

- 已将 service 中的时间生成从 `datetime.utcnow()` 调整为 timezone-aware `datetime.now(UTC)`，消除测试告警。
