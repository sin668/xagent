# P1-E3-S2 执行结果

Story：`docs/stories/phase-1-small-run/P1-E3-S2-staging-lead-detail-evidence.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、移动端对接、测试与构建验证；真实 PostgreSQL/Redis 接口级验证待当前工具出网/审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划、`docs/AI协同开发执行标准.md` 和 superpowers TDD/verification 规范执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

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

## 3. 实现内容

### 3.1 后端 staging 详情

`GET /staging-leads/{lead_id}` 从基础 `StagingLeadResponse` 扩展为 `StagingLeadDetailResponse`，返回：

- `staging_lead`
- `candidate_url`
- `latest_page_snapshot`
- `ai_audit_summary`
- `core_gate`

`latest_page_snapshot` 只返回证据摘要字段，不返回完整网页正文 `text_excerpt`。

### 3.2 core 准入闸门

新增 `StagingLeadService.core_gate_status`，阻断以下情况：

- 缺少来源链接
- 缺少来源证据
- High 来源未完成 Low/Medium 二次复核
- Invalid / Watch
- `not_eligible` / `blocked` 队列状态

### 3.3 移动端详情页

移动端详情页优先读取 `/staging-leads/{id}`，并通过 `mapStagingLeadDetailToLeadDetail` 映射为现有详情视图模型。页面新增“准入闸门”区块，展示：

- 能否进入 core
- 阻断或放行原因
- AI 审计模型和 prompt 版本
- 最新页面快照标题、读取状态和采集时间

底部主按钮叠加 `coreGate.canPromoteToCore` 与证据状态，无来源或无证据时禁用。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 详情 API 返回 staging lead | 通过 | `StagingLeadDetailResponse.staging_lead` |
| 详情 API 返回 candidate URL | 通过 | `CandidateUrlEvidenceResponse` |
| 详情 API 返回 page snapshot | 通过 | `PageSnapshotEvidenceResponse` |
| 详情 API 返回 AI audit summary | 通过 | `AIAuditSummaryResponse` |
| 详情页展示来源链接和证据备注 | 通过 | 移动端 adapter + `detail.vue` 证据区 |
| 详情页展示推荐等级和推荐原因 | 通过 | `aiRecommendation.suggestion/reason` |
| 详情页展示能否进入 core 的原因 | 通过 | `coreGate.reasons` 与“准入闸门”区块 |
| 无证据或无来源时禁止晋级按钮 | 通过 | `buildLeadDetailViewModel` gate 逻辑 |
| 不展示完整网页内容 | 通过 | staging 详情 schema 不含 `text_excerpt` |
| 不展示无关私人内容或关系链 | 通过 | 仅展示公开来源、证据摘要和审计摘要 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_lead_detail_evidence.py -q
npm --prefix apps/mobile test
```

结果：

- 后端失败：`serialize_staging_lead_detail` 尚不存在。
- 移动端失败：缺少 `mapStagingLeadDetailToLeadDetail`，且详情 view model 没有 core gate 字段。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_lead_detail_evidence.py -q
```

结果：

```text
3 passed in 0.56s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py apps/api/tests/test_staging_lead_detail_evidence.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q
```

结果：

```text
72 passed in 0.47s
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260529_0016 (head)
```

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0
npm --prefix apps/mobile test
```

结果：

```text
44 passed
```

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0
npm --prefix apps/mobile run build:h5
```

结果：

```text
DONE  Build complete.
```

## 6. 两轮独立评审

### 6.1 第一轮：需求、契约与风控评审

结论：通过。

发现项：

- 原详情接口只返回 staging lead 基础字段，缺少 candidate URL、page snapshot、AI audit summary 和准入闸门。
- 原移动端详情页优先读取 core customer，不符合 staging 复核详情优先展示证据和准入原因的需求。
- 详情页必须避免展示完整网页正文。

修正结果：

- 新增 `StagingLeadDetailResponse` 作为详情响应契约。
- 移动端详情页优先读取 `/staging-leads/{id}`，失败后回退 core customer/seed。
- `PageSnapshotEvidenceResponse` 不包含 `text_excerpt`。

### 6.2 第二轮：实现、测试与集成回归评审

结论：通过，存在真实数据库连接环境残留验证项。

发现项：

- 需要明确无来源、无证据、High 二次复核、Watch/Invalid 和队列不可晋级状态的阻断原因。
- 移动端底部按钮不能只依赖等级判断，还必须叠加 core gate 和证据状态。
- 当前 Codex 沙箱仍不能连接真实 PostgreSQL/Redis，真实库接口数据验证需在可出网环境复验。

修正结果：

- `StagingLeadService.core_gate_status` 明确输出 `status`、`can_promote_to_core` 和阻断原因。
- `buildLeadDetailViewModel` 将 `coreGate.canPromoteToCore` 与 `hasViewableEvidence` 纳入按钮禁用逻辑。
- 运行后端相关回归、移动端 Node 22 测试和 H5 构建，并记录真实库残留验证项。

## 7. 残留风险

- 当前 Codex 沙箱无法连接 `apps/api/.env` 中的真实 PostgreSQL/Redis，接口级真实数据验证需在可出网终端复验。
- 本 Story 只实现详情展示和准入闸门判断，不实现晋级 core 的写入动作；晋级写入属于 `P1-E3-S3-promote-staging-to-core.md`。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E3-S3-promote-staging-to-core.md`
