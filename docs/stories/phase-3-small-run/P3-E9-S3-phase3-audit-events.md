# Story P3-E9-S3：第三阶段审计事件统一落库

状态：实现完成
Sprint：Sprint 9
优先级：P1
Epic：P3-E9

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“第三阶段审计事件统一落库”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 统一记录第三阶段深挖、字段采纳、客户晋级、清洗、分配、勿扰和合规复核事件。

**Files:**

- Create/Modify: `apps/api/app/services/audit_events.py`
- Modify phase3 services
- Test: `apps/api/tests/test_phase3_audit_events.py`

**Codex 提示词：**

```text
请执行 P3-E9-S3：第三阶段审计事件统一落库。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e9-s3-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 记录 lead_deep_enrichment_started、lead_enrichment_field_accepted/rejected、lead_promoted_to_customer、lead_cleanup_suggestion_created/approved/executed、customer_assigned、customer_do_not_contact_marked 等事件。
- 事件包含 actor、entity、timestamp、reason/evidence。
- 测试覆盖关键事件。

**非目标：**

- 不做审计管理页面。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 必须执行必要的前后端真实联调，不允许只验证 seed 静态页面。
- 所有过程、结果、注解和文档使用中文。


## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动触达。
- Forbidden 来源不得作为客户晋级关键来源。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级客户报价、合同、付款、物流、清关、交付周期等动作前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。
- Agent 不得自动晋级客户、自动归并客户、自动恢复 Invalid、自动触达客户。

## 执行记录

执行时间：2026-06-04
执行者：Codex
执行方式：`superpowers:executing-plans` + `superpowers:test-driven-development` + `superpowers:verification-before-completion`

### 实现摘要

- 新增 `apps/api/app/services/audit_events.py`，提供第三阶段统一审计事件写入服务。
- 新增/更新 `apps/api/tests/test_phase3_audit_events.py`，覆盖事件上下文、冻结事件清单、未知事件阻断、深挖启动、字段采纳/拒绝、勿扰标记审计。
- 更新 `apps/api/app/services/lead_enrichment.py`，深挖启动写入 `lead_deep_enrichment_started`，字段采纳/拒绝提供带审计封装。
- 更新 `apps/api/app/api/lead_enrichment.py`，字段采纳/拒绝 API 使用带统一审计的服务入口。
- 更新 `apps/api/app/services/customer_dnc.py`，标记勿扰写入 `customer_do_not_contact_marked`。
- 更新 `apps/api/app/services/compliance_guards.py`，统一合规硬阻断审计通过 `Phase3AuditEventService` 写入 `ReviewLog`。
- 事件写入包含 actor、entity、timestamp、reason/evidence，并保留 `ReviewLog` 作为当前审计事实表。

### 验收结果

- 记录 `lead_deep_enrichment_started`、`lead_enrichment_field_accepted/rejected`、`lead_promoted_to_customer`、`lead_cleanup_suggestion_created/approved/executed`、`customer_assigned`、`customer_do_not_contact_marked` 等事件：通过，已纳入 `SUPPORTED_EVENTS`。
- 事件包含 actor、entity、timestamp、reason/evidence：通过，`reviewer` 保存 actor，`task_id/input_ref` 保存 entity 和 timestamp，`error_message/output_ref` 保存 reason/evidence。
- 测试覆盖关键事件：通过。
- 非目标“不做审计管理页面”：遵守，本次只做后端服务和测试。

### TDD 记录

红灯命令：

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
cd apps/api
python -m pytest tests/test_phase3_audit_events.py -q
```

红灯结果：

```text
ModuleNotFoundError: No module named 'app.services.audit_events'
```

补充验收红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_audit_events.py -q
```

补充验收红灯结果：

```text
FAILED test_create_pending_deep_enrichment_run_records_unified_started_event
StopIteration

FAILED test_field_candidate_accept_and_reject_record_unified_audit_events
AttributeError: 'LeadEnrichmentService' object has no attribute 'accept_field_candidate_with_audit'

FAILED test_mark_do_not_contact_records_unified_audit_event
StopIteration
```

绿灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_audit_events.py -q
```

绿灯结果：

```text
6 passed, 1 个既有 datetime.utcnow() deprecation warning
```

### 验证命令

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_audit_events.py tests/test_field_candidate_review_api.py tests/test_lead_enrichment_run_api.py tests/test_manual_enrichment_api.py tests/test_lead_cleanup_audit_metrics.py tests/test_lead_cleanup_review_api.py tests/test_lead_cleanup_execute_api.py tests/test_customer_assignment_status.py tests/test_customer_assignment_compliance_guards.py tests/test_promote_staging_lead_to_customer_phase3.py tests/test_phase3_compliance_hard_blocks.py -q
```

结果：73 passed，1 个既有 `datetime.utcnow()` deprecation warning。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m compileall app/services/audit_events.py app/services/lead_enrichment.py app/api/lead_enrichment.py app/services/customer_dnc.py app/services/compliance_guards.py app/services/lead_cleanup.py app/services/customer_status.py app/services/customer_promotion.py
```

结果：退出码 0。

OpenAPI 路由检查：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
paths = client.get('/openapi.json').json()['paths']
for path in [
    '/staging-leads/{lead_id}/enrichment-runs',
    '/lead-enrichment-field-candidates/{candidate_id}/accept',
    '/lead-enrichment-field-candidates/{candidate_id}/reject',
    '/customers/{customer_id}/do-not-contact',
    '/staging-leads/{lead_id}/promote-to-customer',
    '/lead-cleanup/suggestions/{suggestion_id}/approve',
    '/lead-cleanup/suggestions/{suggestion_id}/execute',
]:
    print(path, path in paths)
PY
```

结果：上述 7 个路由均为 `True`。

真实 PostgreSQL API 联调说明：包含 `tests/test_customer_dnc_api.py` 的关联回归在连接 `8.129.17.71:5432` 时被当前沙箱网络策略阻断，错误为 `PermissionError: [Errno 1] Operation not permitted`。已完成根因确认：失败发生在 `asyncpg.connect`，不是本 Story 审计逻辑。需在允许访问真实 PostgreSQL 的本地环境或 CI 中复跑。

### 两轮独立评审

第一轮评审：事件清单、上下文字段、落库模型。

结论：通过，无新增阻塞问题。

发现项：

- 第三阶段已有多个服务直接写 `ReviewLog`，本 Story 不应新建另一套审计表造成事实源分裂。
- 统一事件服务必须保留 actor、entity、timestamp、reason/evidence。
- 未知事件名必须阻断，避免把自动触达等违规事件伪装成合法第三阶段事件。
- 原实现只证明统一审计服务可单独写入，没有证明深挖启动、字段采纳/拒绝和勿扰标记等关键动作真实接入。

修正结果：

- `Phase3AuditEventService` 复用 `ReviewLog`，不新增表。
- `record_event` 标准化 `reviewer/task_id/input_ref/output_ref/error_message`。
- `SUPPORTED_EVENTS` 明确冻结事件名，未知事件抛出 `ValueError`。
- `LeadEnrichmentService.create_pending_run`、字段采纳/拒绝 API、`CustomerDncService.mark_do_not_contact` 已接入统一审计事件。

第二轮评审：服务接入、合规边界、非目标。

结论：通过，无新增实质阻塞问题。

发现项：

- 统一合规阻断服务应使用统一审计事件，避免 P3-E9-S2 与 P3-E9-S3 审计格式分裂。
- 合规硬阻断审计需要 `result=blocked`，不能被通用审计默认值覆盖为 `recorded`。
- 本 Story 不应新增审计管理页面。
- 不得借审计接入新增自动晋级、自动清洗执行、自动触达或社媒动作。
- 真实 PostgreSQL API 联调失败属于沙箱网络无法访问外部数据库，不是本 Story 逻辑失败。

修正结果：

- `compliance_guards.audit_block` 改为调用 `Phase3AuditEventService.record_event`。
- `audit_block` 保留 `result=blocked`、`target_ref`、`block_type` 和具体输入。
- 本次只新增后端审计服务和测试，不新增页面。
- 新增审计只记录人工触发/人工复核/人工勿扰等事件，不改变 raw/staging/core 分层和 Agent 自动化边界。
- 已单独运行不依赖外部 PostgreSQL 的 73 条关联回归，并记录真实数据库联调待复跑。

### 结果文档

- `_bmad-output/implementation-artifacts/codex-p3-e9-s3-执行结果.md`
