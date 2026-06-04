# Story P2-E1-S3：创建 `lead_source_candidates` 数据表、模型和默认风险准入规则

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P2-E1

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“创建 `lead_source_candidates` 数据表、模型和默认风险准入规则”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 建立来源候选池，承载 LLM 自动发现但尚未绑定客户的来源。

**Files:**

- Create: `apps/api/alembic/versions/20260602_0022_create_lead_source_candidates.py`
- Create: `apps/api/app/models/lead_source_candidate.py`
- Create: `apps/api/app/schemas/lead_source_candidate.py`
- Create: `apps/api/app/services/lead_source_candidate_rules.py`
- Modify: `apps/api/app/models/__init__.py`
- Test: `apps/api/tests/test_lead_source_candidate_model.py`

**Codex 提示词：**

```text
请执行 P2-E1-S3：创建 lead_source_candidates 数据表、模型和默认风险准入规则。

要求：
1. 使用 superpowers:test-driven-development。
2. 创建 lead_source_candidates migration、model、schema 和风险默认规则 service。
3. 字段包含 source_url、normalized_domain、platform、channel_name、country、city、risk_level、review_status、approved_for_extraction、reviewer_id、review_note、reviewed_at、discovery_method、discovery_query、discovery_reason、evidence_note、evidence_links、llm_provider、llm_model、llm_output_json、confidence_score、extraction_status、last_extracted_at、next_retry_at、retry_count、dedupe_key、duplicate_of_id、is_duplicate、created_by_task_run_id、created_at、updated_at。
4. 不绑定 customer_id，不修改正式 lead_sources 语义。
5. Low/Medium 默认 auto_approved + approved_for_extraction=true。
6. High 默认 high_risk_review + approved_for_extraction=false。
7. Forbidden 默认 rejected + approved_for_extraction=false。
8. 运行 pytest apps/api/tests/test_lead_source_candidate_model.py。
9. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e1-s3-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 来源候选池不污染正式客户来源。
- 默认风险准入规则有测试。

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

- `apps/api/alembic/versions/20260602_0022_create_lead_source_candidates.py`
- `apps/api/app/models/lead_source_candidate.py`
- `apps/api/app/schemas/lead_source_candidate.py`
- `apps/api/app/services/lead_source_candidate_rules.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/__init__.py`
- `apps/api/tests/test_lead_source_candidate_model.py`
- `_bmad-output/implementation-artifacts/codex-p2-e1-s3-执行结果.md`

### 验收结果

- 已创建 `lead_source_candidates` Alembic migration，revision 为 `20260602_0022`，down_revision 为 `20260602_0021`。
- 已创建 `LeadSourceCandidate` SQLAlchemy model。
- 已创建 `LeadSourceCandidateCreate`、`LeadSourceCandidateUpdate`、`LeadSourceCandidateResponse`、`LeadSourceCandidateListResponse` Pydantic schema。
- 已新增 `LeadSourceCandidateReviewStatus` 和 `LeadSourceCandidateExtractionStatus` 枚举。
- 已实现 `LeadSourceCandidateRules.resolve_defaults` 和 `build_dedupe_key`。
- Low/Medium 默认 `auto_approved + approved_for_extraction=true`。
- High 默认 `high_risk_review + approved_for_extraction=false`。
- Forbidden 默认 `rejected + approved_for_extraction=false + extraction_status=blocked`。
- `lead_source_candidates` 未绑定 `customer_id`，未修改正式 `lead_sources.customer_id` 必填语义。
- 未执行下一个 Story。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q`：20 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/lead_source_candidate.py apps/api/app/schemas/lead_source_candidate.py apps/api/app/services/lead_source_candidate_rules.py apps/api/alembic/versions/20260602_0022_create_lead_source_candidates.py apps/api/tests/test_lead_source_candidate_model.py`：通过。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260602_0022 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260602_0021:head --sql`：成功生成 PostgreSQL offline SQL，包含 `CREATE TABLE lead_source_candidates`、新增 review/extraction 枚举、`agent_task_runs` 外键和去重唯一约束。

### 风控结果

- 未新增自动社交私信、自动加好友、登录后批量采集或反爬规避能力。
- 未改变 High/Forbidden 风险边界。
- 未将来源候选直接写入正式 `lead_sources`。
- 未实现 Agent 自动运行、LLM 调用、来源审核 API 或抽取消费。

### 双轮评审记录

#### 第一轮评审：Story 范围与需求一致性

结论：通过。

发现项：

- 实现覆盖 Story 要求的 `lead_source_candidates` 表、模型、schema 和默认风险准入规则。
- 字段覆盖 source_url、domain、platform、channel、国家城市、风险审核、证据、LLM 输出、抽取状态、去重和审计字段。
- 未绑定 `customer_id`，未污染正式 `lead_sources`。

修正结果：

- 无需修正。

#### 第二轮评审：测试、迁移与合规边界

结论：通过。

发现项：

- P2-E1 三个 Story 回归测试通过：20 passed。
- 新增 Python 文件编译通过。
- Alembic offline SQL 生成成功，迁移链 head 为 `20260602_0022`。
- 初版 migration 曾会重复创建既有 `sourceplatform` 和 `channelrisklevel` 枚举，已修正为复用既有枚举，仅创建本 Story 新增 review/extraction 枚举。
- 本 Story 仅建立来源候选数据模型和默认规则，不引入采集、触达或自动消费能力。

修正结果：

- 已将 migration 中 `sourceplatform` 和 `channelrisklevel` 调整为 `postgresql.ENUM(..., create_type=False)` 复用既有枚举。
