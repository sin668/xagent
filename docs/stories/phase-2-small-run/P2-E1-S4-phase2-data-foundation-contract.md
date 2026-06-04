# Story P2-E1-S4：模型导入、migration 验证和数据层契约测试

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E1

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“模型导入、migration 验证和数据层契约测试”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 确认三张第二阶段核心表在真实 PostgreSQL migration 链路中可用。

**Files:**

- Modify: `apps/api/app/models/__init__.py`
- Modify: `apps/api/app/db/base.py`
- Test: `apps/api/tests/test_phase2_data_foundation.py`
- Output: `_bmad-output/implementation-artifacts/codex-p2-e1-s4-执行结果.md`

**Codex 提示词：**

```text
请执行 P2-E1-S4：模型导入、migration 验证和数据层契约测试。

要求：
1. 使用 superpowers:test-driven-development。
2. 检查三张表的 model 是否被 Alembic/env 和 metadata 正确加载。
3. 编写数据层契约测试，覆盖 llm_prompt_templates、agent_task_runs、lead_source_candidates 的最小插入和查询。
4. 使用 apps/api/.env 的真实 PostgreSQL 连接进行 migration 验证；如沙箱网络阻断，必须记录阻断原因和本地可执行命令。
5. 不实现 API，不实现前端。
6. 运行 pytest apps/api/tests/test_phase2_data_foundation.py。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e1-s4-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 三张表可被 metadata 发现。
- migration 链路结果明确。
- 真实 PostgreSQL 验证结果或阻断原因已记录。

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

- 新增 `apps/api/tests/test_phase2_data_foundation.py`。
- 验证 `llm_prompt_templates`、`agent_task_runs`、`lead_source_candidates` 已被 `Base.metadata` 发现。
- 验证 `lead_source_candidates` 与正式 `lead_sources` 的数据边界：候选来源不绑定 `customer_id`，正式来源仍要求 `customer_id` 必填。
- 验证 migration 链路线性：
  - `20260529_0019 -> 20260602_0020`
  - `20260602_0020 -> 20260602_0021`
  - `20260602_0021 -> 20260602_0022`
- 验证 `20260602_0022` 复用既有 `sourceplatform` 和 `channelrisklevel` enum，避免真实 PostgreSQL 重复创建类型。
- 验证三张核心表的最小 insert/select 语句可用 PostgreSQL dialect 编译。
- 验证当前 Story 未提前实现来源审核 API 或 Source Discovery Agent 模块。
- 使用 `apps/api/.env` 配置的真实 PostgreSQL 执行 migration，并确认三张表已真正落库。

未执行：

- 未实现 API。
- 未实现前端。
- 未执行 P2-E2-S1 或其他后续 Story。

## 验证结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase2_data_foundation.py -q
```

结果：

```text
6 passed in 0.31s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
26 passed in 0.39s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/tests/test_phase2_data_foundation.py
```

结果：通过，退出码 0。

```bash
cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260602_0022 (head)
```

```bash
cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0019:head --sql
```

结果：成功生成 PostgreSQL offline SQL，覆盖三段升级，并包含三张表的建表 SQL。

真实 PostgreSQL 验证：

- 首次在沙箱内执行 `alembic current` 被网络权限阻断，错误为 `PermissionError: [Errno 1] Operation not permitted`。
- 沙箱外执行 `alembic current` 显示真实库初始版本为 `20260529_0019`。
- 沙箱外执行 `alembic upgrade head` 成功运行三段 migration。
- 独立只读查询确认：

```text
alembic_version= 20260602_0022
tables= ['agent_task_runs', 'lead_source_candidates', 'llm_prompt_templates']
counts= {'llm_prompt_templates': 0, 'agent_task_runs': 0, 'lead_source_candidates': 0}
```

## 两轮独立评审记录

### 第一轮评审：数据模型、migration 和 Story 范围

结论：通过。

发现项：

- 三张第二阶段核心表均可被 SQLAlchemy metadata 发现。
- migration 链路保持单 head，真实库已从 `20260529_0019` 升级到 `20260602_0022`。
- 候选来源表未绑定 `customer_id`，没有污染正式 `lead_sources` 的客户关系约束。
- 本 Story 未越界实现 API、前端、Agent 自动运行或触达逻辑。

修正结果：

- 无新增阻塞问题，无需修正。

### 第二轮评审：测试证据、真实库验证和合规边界

结论：通过。

发现项：

- 目标测试 6 条通过，P2-E1 回归测试 26 条通过。
- 新增测试文件 Python 编译通过。
- Alembic offline SQL 可生成，真实 PostgreSQL 表存在性已通过独立查询确认。
- 三张表当前记录数为 0，符合本 Story 只验证数据底座、不写入业务 seed 的范围。
- 未触发自动社交私信、加好友、登录后批量采集、反爬规避或非公开数据抓取。

修正结果：

- 无新增实质阻塞问题，无需修正。
