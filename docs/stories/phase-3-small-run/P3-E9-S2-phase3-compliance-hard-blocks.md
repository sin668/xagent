# Story P3-E9-S2：第三阶段合规硬阻断规则统一服务

状态：实现完成
Sprint：Sprint 9
优先级：P0
Epic：P3-E9

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“第三阶段合规硬阻断规则统一服务”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 统一实现勿扰、Forbidden、C 级复核、自动触达禁止、无证据字段采纳等硬阻断。

**Files:**

- Create/Modify: `apps/api/app/services/compliance_guards.py`
- Modify promotion/enrichment/followup/cleanup services
- Test: `apps/api/tests/test_phase3_compliance_hard_blocks.py`

**Codex 提示词：**

```text
请执行 P3-E9-S2：第三阶段合规硬阻断规则统一服务。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e9-s2-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 勿扰阻断触达草稿和主动触达记录。
- Forbidden 阻断客户晋级关键来源。
- C 级报价/合同/付款/物流/清关/交付周期动作前需复核。
- 无证据关键字段不得采纳为晋级字段。
- 所有阻断有审计。

**非目标：**

- 不做合规审批页面。

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

- 新增 `apps/api/app/services/compliance_guards.py`，统一第三阶段硬阻断规则和阻断审计。
- 新增 `apps/api/tests/test_phase3_compliance_hard_blocks.py`，覆盖勿扰触达阻断、Forbidden 晋级关键来源阻断、C 级交易动作复核阻断、无证据字段采纳阻断、自动触达阻断。
- 更新 `CustomerDncService.record_outreach_result`，触达记录创建前统一校验勿扰和人工确认。
- 更新 `OutreachDraftService.get_existing_draft`，勿扰触达草稿阻断接入统一合规守卫并可写入阻断审计。
- 更新 `LeadEnrichmentService.validate_candidate_has_evidence_for_acceptance`，关键字段采纳统一走合规守卫。
- 更新 `CustomerPromotionService.build_promotion_payloads`，Forbidden 来源不得作为客户晋级关键来源。
- 更新 `StagingLeadService.core_gate_status` 和 `promote_staging_lead_to_core`，Forbidden 来源在 staging 晋级门禁和实际晋级路径均被硬阻断。
- 更新 `CustomerAssignmentStatusService.transition_status`，C 级报价/合同边界保留原业务审计，同时追加统一合规阻断审计。

### 验收结果

- 勿扰阻断触达草稿和主动触达记录：通过。
- Forbidden 阻断客户晋级关键来源：通过。
- C 级报价/合同/付款/物流/清关/交付周期动作前需复核：通过。
- 无证据关键字段不得采纳为晋级字段：通过。
- 所有阻断有审计：通过，统一使用 `ReviewLog(action="phase3_compliance_block", result="blocked")`。
- 非目标“不做合规审批页面”：遵守，本次只做后端统一守卫服务，不新增页面。

### TDD 记录

红灯命令：

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
cd apps/api
python -m pytest tests/test_phase3_compliance_hard_blocks.py -q
```

红灯结果：

```text
ModuleNotFoundError: No module named 'app.services.compliance_guards'
```

补充验收红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_compliance_hard_blocks.py -q
```

补充验收红灯结果：

```text
FAILED test_forbidden_source_is_blocked_by_staging_core_gate
assert True is False

FAILED test_outreach_draft_dnc_block_uses_unified_guard_and_records_audit
TypeError: OutreachDraftService.get_existing_draft() got an unexpected keyword argument 'session'
```

绿灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_compliance_hard_blocks.py -q
```

绿灯结果：

```text
7 passed
```

### 验证命令

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_compliance_hard_blocks.py tests/test_field_candidate_review_api.py tests/test_lead_enrichment_run_api.py tests/test_manual_enrichment_api.py tests/test_lead_cleanup_review_api.py tests/test_lead_cleanup_execute_api.py tests/test_outreach_draft_api.py tests/test_phase3_permission_guards.py -q
```

结果：53 passed，2 个既有 `datetime.utcnow()` deprecation warning。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m compileall app/services/compliance_guards.py app/services/lead_enrichment.py app/services/customer_promotion.py app/services/customer_dnc.py app/services/customer_status.py app/services/outreach_draft.py app/services/staging_leads.py
```

结果：退出码 0。

真实 PostgreSQL API 联调说明：当前执行环境网络受限，前一轮真实数据库 API 测试在连接 `8.129.17.71:5432` 时被 `PermissionError: [Errno 1] Operation not permitted` 阻断；本 Story 未继续重复相同受限命令。需在允许访问真实 PostgreSQL 的本地环境或 CI 中复跑数据库联调用例。

### 两轮独立评审

第一轮评审：硬阻断覆盖范围、审计一致性、服务接入点。

结论：通过，无新增阻塞问题。

发现项：

- 现有阻断分散在触达、晋级、字段采纳、状态流转服务中，缺少统一审计格式。
- 触达草稿原先只有本地 `block_reasons`，没有接入统一合规 guard，导致勿扰草稿阻断无法形成统一审计。
- `StagingLeadService.core_gate_status` 原先未明确把 `Forbidden` 作为晋级硬阻断，存在门禁误判 ready 的风险。
- C 级状态流转已有业务审计，新增统一审计时不能破坏既有测试和既有审计口径。
- 自动触达阻断应基于 `sent + manual_confirmed=False`，不能影响草稿和人工确认记录。

修正结果：

- 新增 `Phase3ComplianceGuardService`，统一 `phase3_compliance_block` 审计格式。
- `OutreachDraftService.get_existing_draft` 支持 `session/actor`，勿扰草稿阻断调用统一 guard 并保留页面原有阻断展示。
- `StagingLeadService.core_gate_status` 增加 `Forbidden 来源不得作为客户晋级关键来源` 原因，实际晋级路径调用统一 guard 写入阻断审计。
- C 级状态流转保留 `customer_compliance_review_requested` 为第一条业务审计，再追加统一合规阻断审计。
- 触达服务仅阻断勿扰客户和未人工确认的 sent 记录。

第二轮评审：非目标、数据分层、风控边界。

结论：通过，无新增实质阻塞问题。

发现项：

- 本 Story 不应新增合规审批页面或动态审批流。
- 统一服务不得让 AI 或 Agent 自动晋级、自动归并、自动恢复 Invalid、自动触达。
- Forbidden、无证据字段、勿扰、C 级复核必须作为硬阻断，不是前端提示。
- 本轮补强仅影响服务层参数和门禁判断，未改变现有 API 默认响应结构和移动端可用字段。

修正结果：

- 本次只新增后端守卫服务和测试，不新增页面。
- 接入点均为人工关键动作或服务校验入口，未新增 Agent 自动动作。
- 阻断均在服务层执行，并写入 `ReviewLog`。
- 触达草稿 API 原有测试保持通过，证明移动端触达助手既有展示未被破坏。

### 结果文档

- `_bmad-output/implementation-artifacts/codex-p3-e9-s2-执行结果.md`
