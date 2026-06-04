# P1-E3-S3 执行结果

Story：`docs/stories/phase-1-small-run/P1-E3-S3-promote-staging-to-core.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、移动端动作对接、测试与构建验证；真实 PostgreSQL 接口级写入验证待当前工具出网/审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划、`docs/AI协同开发执行标准.md` 和 superpowers TDD/verification 规范执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

- `apps/api/app/services/staging_leads.py`
- `apps/api/app/schemas/staging_leads.py`
- `apps/api/app/api/staging_leads.py`
- `apps/api/tests/test_promote_staging_to_core.py`
- `apps/mobile/src/services/leadDetail.js`
- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/tests/leadDetail.test.mjs`
- `docs/stories/phase-1-small-run/P1-E3-S3-promote-staging-to-core.md`
- `_bmad-output/implementation-artifacts/codex-p1-e3-s3-执行结果.md`

## 3. 实现内容

### 3.1 后端人工晋级 API

新增：

```text
POST /staging-leads/{lead_id}/promote
```

请求必须包含：

- `actor`
- `review_result=approved`
- `review_note`

返回：

- staging lead id
- core customer id
- customer external id
- customer status
- 勿扰状态
- 是否需要合规复核
- compliance review id
- review log id

### 3.2 staging 到 core 写入

Promote 成功后写入或更新：

- `customers`
- `lead_sources`
- `contact_methods`
- `review_logs`
- C 级时的 `compliance_reviews`

映射规则：

- `Customer.external_id = staging:{staging_lead_id}`
- `ReviewLog.input_ref = staging:{staging_lead_id}`
- `ReviewLog.output_ref = customer:{customer_id}`

### 3.3 准入阻断

以下情况阻断晋级：

- 来源链接缺失
- 证据备注缺失
- High 未完成二次复核
- Invalid / Watch
- `not_eligible` / `blocked` 队列状态

### 3.4 移动端人工动作

移动端详情页底部主按钮在 staging 详情中调用：

```text
POST /staging-leads/{id}/promote
```

该动作只提交人工复核通过结果，不自动触达、不自动发送话术。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 来源链接缺失不得晋级 | 通过 | `validate_promote_allowed` 测试覆盖 |
| 证据备注缺失不得晋级 | 通过 | `validate_promote_allowed` 测试覆盖 |
| High 未二次复核不得晋级 | 通过 | High 且非 `approved` review_status 阻断 |
| Invalid/Watch 不得晋级到待触达 | 通过 | gate 阻断 Invalid/Watch |
| C 级晋级后必须带合规复核标记 | 通过 | C 级创建或复用 pending `ComplianceReview` |
| 勿扰状态必须保留 | 通过 | existing customer `do_not_contact` 不被清空 |
| 写入或更新 customers | 通过 | service 实现 |
| 写入 contact_methods | 通过 | service 实现并去重 |
| 写入 lead_sources | 通过 | service 实现 |
| 保留 staging 与 core 映射 | 通过 | `external_id` + `review_logs` |
| 写 review_logs | 通过 | `promote_staging_to_core` 写入 |
| 不自动触达客户 | 通过 | 未调用 outreach/send 能力 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_promote_staging_to_core.py -q
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0
npm --prefix apps/mobile test
```

结果：

- 后端失败：`StagingPromoteRequest` 尚不存在。
- 移动端失败：`buildPromoteStagingPayload` 尚未导出。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_promote_staging_to_core.py -q
```

结果：

```text
4 passed in 0.29s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py apps/api/tests/test_promote_staging_to_core.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_promote_staging_to_core.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q
```

结果：

```text
76 passed in 0.52s
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
45 passed
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

### 5.3 真实数据库验证残留

尝试纳入既有真实 PostgreSQL 相关 `compliance_review_api` / `customer_dnc_service` 测试时，当前 Codex 沙箱在连接 `apps/api/.env` 配置的 PostgreSQL 时失败：

```text
PermissionError: [Errno 1] Operation not permitted
address = ('8.129.17.71', 5432)
```

该失败属于当前工具环境网络权限限制，不作为本 Story 代码逻辑通过的证据；真实库写入仍需在可出网环境复验。

## 6. 两轮独立评审

### 6.1 第一轮：需求、数据映射与风控评审

结论：通过。

发现项：

- Story 要求“保留 staging 与 core 的映射”，当前模型没有专用映射表或字段。
- High 风险规则不能简单永久阻断，Story 明确是“High 未二次复核不得晋级”。
- C 级晋级必须和报价/合同前合规复核联动。

修正结果：

- 采用 `Customer.external_id = staging:{staging_lead_id}` 保留映射，`ReviewLog.input_ref/output_ref` 同步记录映射。
- 调整 `core_gate_status`：High 只有未 `approved` 二次复核时阻断。
- Promote 时为 C 级创建或复用 `ComplianceReview(status=pending)`。

### 6.2 第二轮：实现、测试与边界评审

结论：通过，存在真实数据库连接环境残留验证项。

发现项：

- 勿扰状态不能因 upsert customer 被清空。
- 重复 promote 不应重复创建联系方式和合规复核记录。
- 移动端只能发起人工晋级请求，不能扩展为自动触达。
- 当前 Codex 沙箱无法连接真实 PostgreSQL，接口级写入验证未完成。

修正结果：

- `build_core_customer_payload` 保留既有 customer 的 `do_not_contact` 和状态。
- 联系方式按 `customer_id + method_type + value` 去重；C 级合规复核复用已有最新记录。
- 移动端仅调用 `/staging-leads/{id}/promote`，未调用触达发送接口。
- 将真实库验证阻塞原因写入测试结果和执行产物。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL，`POST /staging-leads/{id}/promote` 的真实库写入需在可出网终端复验。
- 本 Story 使用 `Customer.external_id` 和 `ReviewLog` 保留 staging-core 映射；如后续需要多对多历史映射，可在独立 Story 增加专用映射表。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E3-S4-dedupe-merge-suggestions.md`
