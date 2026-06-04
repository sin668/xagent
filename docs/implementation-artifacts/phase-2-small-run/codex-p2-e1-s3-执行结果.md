# P2-E1-S3 执行结果：创建 `lead_source_candidates` 数据表、模型和默认风险准入规则

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E1-S3-lead-source-candidates-data-model.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E1-S3，不执行下一个 Story。

已完成：

- 创建 `lead_source_candidates` Alembic migration。
- 创建 `LeadSourceCandidate` SQLAlchemy model。
- 创建 `LeadSourceCandidateCreate`、`LeadSourceCandidateUpdate`、`LeadSourceCandidateResponse`、`LeadSourceCandidateListResponse` Pydantic schema。
- 新增 `LeadSourceCandidateReviewStatus` 和 `LeadSourceCandidateExtractionStatus` 枚举。
- 实现 `LeadSourceCandidateRules.resolve_defaults` 和 `build_dedupe_key`。
- 测试覆盖 Low/Medium/High/Forbidden 默认风险准入规则。
- 测试覆盖 `lead_source_candidates` 不绑定 `customer_id`。

未执行：

- 未实现来源候选 upsert service。
- 未实现 Source Discovery Agent。
- 未实现来源审核 API。
- 未实现 `LEAD_EXTRACTION` 消费。
- 未执行 P2-E1-S4 或其他 Story。

## 2. 修改文件

- `apps/api/alembic/versions/20260602_0022_create_lead_source_candidates.py`
- `apps/api/app/models/lead_source_candidate.py`
- `apps/api/app/schemas/lead_source_candidate.py`
- `apps/api/app/services/lead_source_candidate_rules.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/__init__.py`
- `apps/api/tests/test_lead_source_candidate_model.py`
- `docs/stories/phase-2-small-run/P2-E1-S3-lead-source-candidates-data-model.md`

## 3. TDD 记录

RED：

- 先创建 `apps/api/tests/test_lead_source_candidate_model.py`。
- 首次运行 `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_model.py -q`。
- 结果：失败，原因是 `LeadSourceCandidateExtractionStatus` 尚不存在。

GREEN：

- 新增枚举、模型、schema、规则 service 和 migration。
- 运行目标测试，通过。
- 检查 Alembic offline SQL 时发现 migration 会重复创建既有 `sourceplatform` 和 `channelrisklevel` 枚举。
- 修正 migration，复用既有枚举，仅创建本 Story 新增的 review/extraction 状态枚举。

## 4. 验证命令与结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
20 passed in 0.52s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/lead_source_candidate.py apps/api/app/schemas/lead_source_candidate.py apps/api/app/services/lead_source_candidate_rules.py apps/api/alembic/versions/20260602_0022_create_lead_source_candidates.py apps/api/tests/test_lead_source_candidate_model.py
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
cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260602_0021:head --sql
```

结果：成功生成 PostgreSQL offline SQL，包含：

- `CREATE TYPE leadsourcecandidatereviewstatus`
- `CREATE TYPE leadsourcecandidateextractionstatus`
- `CREATE TABLE lead_source_candidates`
- `FOREIGN KEY(created_by_task_run_id) REFERENCES agent_task_runs (id) ON DELETE SET NULL`
- `CONSTRAINT uq_lead_source_candidates_dedupe_key UNIQUE (dedupe_key)`

## 5. 验收结果

- 来源候选池不绑定 `customer_id`，不污染正式 `lead_sources`。
- `lead_sources.customer_id` 仍为必填，并保留客户外键。
- Low/Medium 默认进入自动抽取准入。
- High 默认进入高风险人工复核，不自动抽取。
- Forbidden 默认驳回并阻断抽取。
- 默认风险准入规则和 dedupe key 均有测试覆盖。

## 6. 风控结果

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- 未改变 High/Forbidden 风险边界。
- 未引入触达、采集、抽取或自动调度能力。

## 7. 双轮评审记录

### 第一轮评审：Story 范围与需求一致性

结论：通过。

发现项：

- 已完成 Story 指定的 migration、model、schema 和风险默认规则 service。
- 字段覆盖 Story 要求的全部来源、风险、证据、LLM、队列、去重和审计字段。
- 实现未扩展到来源 upsert、审核 API、Agent 或 LEAD_EXTRACTION。

修正结果：

- 无需修正。

### 第二轮评审：测试、迁移与合规边界

结论：通过。

发现项：

- P2-E1 三个 Story 回归测试通过：20 passed。
- 新增 Python 文件编译通过。
- Alembic offline SQL 生成成功，迁移链 head 为 `20260602_0022`。
- 已修正 migration 复用既有 `sourceplatform` 和 `channelrisklevel` 枚举，避免真实 PostgreSQL 重复创建类型。
- 本 Story 只建立来源候选池，不涉及自动采集或客户触达。

修正结果：

- 已将 migration 中既有枚举调整为 `create_type=False` 复用。
