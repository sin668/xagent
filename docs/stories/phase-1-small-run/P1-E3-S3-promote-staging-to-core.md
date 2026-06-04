# Story P1-E3-S3：实现人工复核晋级 core

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P1-E3 staging 复核队列

## 用户故事

作为线索运营，我希望把复核通过的 staging 线索晋级到 core 客户库，以便交付客服或销售。

## 业务价值

完成宽进严出的关键闭环。

## 依赖

- P1-E3-S2
- 现有 core customer/contact/source 模型

## 实现范围

- 实现 promote staging lead to core service。
- 写入或更新 customers、contact_methods、lead_sources。
- 保留 staging 与 core 的映射。
- 写 review_logs。

## 数据/API 影响

- 新增 `/staging-leads/{id}/promote` API。

## 验收标准

- 来源链接缺失不得晋级。
- 证据备注缺失不得晋级。
- High 未二次复核不得晋级。
- Invalid/Watch 不得晋级到待触达。
- C 级晋级后必须带合规复核标记。
- 勿扰状态必须保留。

## 非目标

- 不自动触达客户。

## 风控检查

- 晋级动作必须记录操作人、时间和复核结论。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/app/services/staging_leads.py`
- `apps/api/app/schemas/staging_leads.py`
- `apps/api/app/api/staging_leads.py`
- `apps/api/tests/test_promote_staging_to_core.py`
- `apps/mobile/src/services/leadDetail.js`
- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/tests/leadDetail.test.mjs`
- `docs/stories/phase-1-small-run/P1-E3-S3-promote-staging-to-core.md`
- `_bmad-output/implementation-artifacts/codex-p1-e3-s3-执行结果.md`

### 验收结果

- 新增 `POST /staging-leads/{lead_id}/promote`，只允许人工复核通过的 staging 线索晋级 core。
- 晋级时写入或更新 `customers`，使用 `external_id = staging:{staging_lead_id}` 保留 staging-core 映射。
- 晋级时写入或更新 `lead_sources`，保留来源 URL、证据备注、来源平台和风险等级。
- 晋级时写入 `contact_methods`，从 staging `contacts_json` 提取公开联系方式。
- 晋级时写 `review_logs`，记录操作人、动作、输入 staging 引用、输出 customer 引用、复核结论和备注。
- 来源链接缺失、证据备注缺失、High 未二次复核、Invalid/Watch、不可晋级队列状态均会阻断晋级。
- C 级晋级后创建或复用待处理合规复核记录，报价/合同前仍由合规模块阻断。
- 已存在的勿扰 customer 晋级更新时保留 `do_not_contact` 和 `do_not_contact` 状态。
- 移动端详情页底部主按钮在 staging 详情可调用 promote API；不做自动触达。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_promote_staging_to_core.py -q`：4 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py apps/api/tests/test_promote_staging_to_core.py`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_promote_staging_to_core.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q`：76 passed。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0016 (head)`。
- `source ~/.zshrc && nvm use v22.22.0 && npm --prefix apps/mobile test`：45 passed。
- `source ~/.zshrc && nvm use v22.22.0 && npm --prefix apps/mobile run build:h5`：Build complete。
- 真实 PostgreSQL 相关既有 `compliance_review_api` / `customer_dnc_service` 测试在当前 Codex 沙箱内被 socket 权限拦截，错误为 `PermissionError: [Errno 1] Operation not permitted`，需要在可出网环境复验。

### 风控结果

- 本 Story 未新增自动触达、自动私信、自动加好友或自动发送能力。
- Promote 请求必须包含 `actor` 和 `review_result=approved`。
- High 来源只有在 review_status 已为 `approved` 时才可能通过准入；未二次复核仍阻断。
- Invalid/Watch 不得晋级 core 或待触达。
- C 级晋级后必须带合规复核标记。

### 两轮独立评审

#### 第一轮：需求、数据映射与风控评审

评审结论：通过。

发现项：

- Story 要求“保留 staging 与 core 的映射”，当前模型没有专用映射表或字段。
- High 风险规则不能简单永久阻断，Story 明确是“High 未二次复核不得晋级”。
- C 级晋级必须和报价/合同前合规复核联动。

修正结果：

- 采用 `Customer.external_id = staging:{staging_lead_id}` 保留映射，`ReviewLog.input_ref/output_ref` 同步记录映射。
- 调整 `core_gate_status`：High 只有未 `approved` 二次复核时阻断。
- Promote 时为 C 级创建或复用 `ComplianceReview(status=pending)`。

#### 第二轮：实现、测试与边界评审

评审结论：通过，存在真实数据库连接环境残留验证项。

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
