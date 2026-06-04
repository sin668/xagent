# Story P1-E3-S2：实现 staging 线索详情与证据视图

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P1-E3 staging 复核队列

## 用户故事

作为复核人员，我希望在线索详情中看到来源证据、AI 推荐原因、缺失字段和准入闸门，以便做出复核决定。

## 业务价值

保证进入 core 的线索有证据、有判断依据。

## 依赖

- P1-E3-S1
- P1-E1-S3

## 实现范围

- 线索详情 API 返回 staging lead、candidate URL、page snapshot、AI audit summary。
- 前端展示来源链接、证据备注、AI 推荐、缺失字段、闸门状态。

## 数据/API 影响

- 扩展 staging detail API。

## 验收标准

- 详情页必须展示来源链接和证据备注。
- 详情页必须展示推荐等级和推荐原因。
- 详情页必须展示能否进入 core 的原因。
- 无证据或无来源时禁止晋级按钮。

## 非目标

- 不展示完整网页内容。

## 风控检查

- 不展示无关私人内容或关系链。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/app/services/staging_leads.py`
- `apps/api/app/schemas/staging_leads.py`
- `apps/api/app/api/staging_leads.py`
- `apps/api/tests/test_staging_lead_detail_evidence.py`
- `apps/mobile/src/services/apiAdapters.js`
- `apps/mobile/src/services/leadDetail.js`
- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/tests/apiAdapters.test.mjs`
- `apps/mobile/tests/leadDetail.test.mjs`
- `docs/stories/phase-1-small-run/P1-E3-S2-staging-lead-detail-evidence.md`
- `_bmad-output/implementation-artifacts/codex-p1-e3-s2-执行结果.md`

### 验收结果

- `GET /staging-leads/{lead_id}` 返回 staging lead、candidate URL、最新 page snapshot 证据摘要、AI audit summary 和 core 准入闸门。
- 详情响应不返回 `text_excerpt`，不展示完整网页正文。
- 移动端详情页优先读取 `/staging-leads/{id}`，展示来源链接、证据备注、AI 推荐等级、推荐原因、缺失字段和准入闸门原因。
- 无来源链接、无来源证据、High 未二次复核、Invalid/Watch、`not_eligible/blocked` 队列状态会阻断进入 core。
- 无证据或无来源时，移动端底部主按钮禁用并显示“待补证据”。
- 本 Story 未新增自动触达、自动加好友、自动私信或自动晋级 core 写入能力。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_lead_detail_evidence.py -q`：3 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py apps/api/tests/test_staging_lead_detail_evidence.py`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q`：72 passed。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0016 (head)`。
- `source ~/.zshrc && nvm use v22.22.0 && npm --prefix apps/mobile test`：44 passed。
- `source ~/.zshrc && nvm use v22.22.0 && npm --prefix apps/mobile run build:h5`：Build complete。

### 风控结果

- 详情页只展示公开来源 URL、证据备注、快照标题、读取状态、采集时间和策略备注，不展示完整网页正文。
- High 来源默认被准入闸门阻断，需完成 Low/Medium 二次复核后再进入后续 core 流程。
- Watch/Invalid 继续被阻断，不进入 core 或触达队列。
- AI 审计信息只展示模型、prompt 版本、推荐等级、推荐原因、缺失字段和风险阻断摘要。

### 两轮独立评审

#### 第一轮：需求、契约与风控评审

评审结论：通过。

发现项：

- 原详情接口只返回 staging lead 基础字段，缺少 candidate URL、page snapshot、AI audit summary 和准入闸门。
- 原移动端详情页优先读取 core customer，不符合 staging 复核详情优先展示证据和准入原因的需求。
- 详情页必须避免展示完整网页正文。

修正结果：

- 新增 `StagingLeadDetailResponse`，包含 `staging_lead`、`candidate_url`、`latest_page_snapshot`、`ai_audit_summary`、`core_gate`。
- 移动端详情页改为优先读取 `/staging-leads/{id}`，失败后才回退 core customer/seed。
- `PageSnapshotEvidenceResponse` 不包含 `text_excerpt`。

#### 第二轮：实现、测试与集成回归评审

评审结论：通过，存在真实数据库连接环境残留验证项。

发现项：

- 需要明确无来源、无证据、High 二次复核、Watch/Invalid 和队列不可晋级状态的阻断原因。
- 移动端按钮不能只依赖等级判断，还必须叠加 core gate 和证据状态。
- 当前 Codex 沙箱仍不能连接真实 PostgreSQL/Redis，真实库接口数据验证需在可出网环境复验。

修正结果：

- `StagingLeadService.core_gate_status` 明确输出 `status`、`can_promote_to_core` 和阻断原因。
- `buildLeadDetailViewModel` 将 `coreGate.canPromoteToCore` 与 `hasViewableEvidence` 纳入底部按钮禁用逻辑。
- 执行后端相关回归、移动端 Node 22 测试和 H5 构建，并记录真实库残留验证项。
