# Story P1-E3-S4：实现重复检测和合并建议

状态：Done  
Sprint：Sprint 2  
优先级：P1  
Epic：P1-E3 staging 复核队列

## 用户故事

作为线索运营，我希望系统提示强重复和疑似重复，以便避免重复触达。

## 业务价值

减少数据污染，提高客户库可信度。

## 依赖

- P1-E1-S4
- core customer/contact/source 模型

## 实现范围

- 强重复：标准化客户名称 + 联系方式 hash。
- 疑似重复：标准化客户名称 + 城市 + 来源域名。
- 来源重复：URL hash。
- 展示重复候选并允许人工处理。

## 数据/API 影响

- 新增 dedupe service。
- staging list/detail 返回 duplicate signals。

## 验收标准

- 强重复必须阻止重复晋级。
- 疑似重复必须进入人工复核，不自动删除。
- 合并后保留所有来源证据。

## 非目标

- 不做复杂机器学习去重。

## 风控检查

- 不因去重丢失勿扰状态。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/app/services/staging_leads.py`
- `apps/api/app/schemas/staging_leads.py`
- `apps/api/app/api/staging_leads.py`
- `apps/api/tests/test_dedupe_merge_suggestions.py`
- `apps/mobile/src/services/apiAdapters.js`
- `apps/mobile/src/services/leadDetail.js`
- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/tests/apiAdapters.test.mjs`
- `apps/mobile/tests/leadDetail.test.mjs`
- `docs/stories/phase-1-small-run/P1-E3-S4-dedupe-merge-suggestions.md`
- `_bmad-output/implementation-artifacts/codex-p1-e3-s4-执行结果.md`

### 验收结果

- 新增 dedupe 规则函数，覆盖强重复、疑似重复和来源 URL hash 重复。
- staging 列表和详情响应新增 `duplicate_signals`。
- 新增 `GET /staging-leads/{lead_id}/duplicates` 查看重复候选。
- 新增 `POST /staging-leads/{lead_id}/duplicates/resolve` 支持 `merge_to_core`、`mark_duplicate`、`dismiss` 人工处理。
- 强重复会阻断 promote 晋级 core。
- 疑似重复只进入人工复核提示，不自动删除。
- `merge_to_core` 会把 staging 来源和联系方式追加到目标 core customer，保留来源证据。
- 去重处理不会修改目标 customer 的勿扰状态。
- 移动端列表展示“强重复阻断 / 疑似重复待复核”标记，详情页展示重复建议并阻断强重复晋级。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_dedupe_merge_suggestions.py -q`：5 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_dedupe_merge_suggestions.py apps/api/tests/test_promote_staging_to_core.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q`：81 passed。
- `source ~/.zshrc && nvm use v22.22.0 && npm --prefix apps/mobile test`：46 passed。
- `source ~/.zshrc && nvm use v22.22.0 && npm --prefix apps/mobile run build:h5`：Build complete。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0016 (head)`。

### 风控结果

- 强重复只阻断晋级，不删除 staging 记录。
- 疑似重复和来源重复只提示人工复核。
- 合并重复时追加 `lead_sources` 与 `contact_methods`，不覆盖目标 customer 勿扰状态。
- 未新增复杂机器学习去重。
- 未新增自动触达能力。

### 两轮独立评审

#### 第一轮：需求、规则和数据保全评审

评审结论：通过。

发现项：

- Story 要求“来源重复：URL hash”，不能只按 URL 字符串完全相等判断。
- 强重复必须阻断 promote，不能只在列表提示。
- 合并重复时必须保留来源证据，不能通过删除 staging 或覆盖 core source 简化处理。

修正结果：

- `build_duplicate_keys` 输出 `source_url_hash`，来源重复按 hash 比对。
- `promote_staging_lead_to_core` 调用 `raise_if_strong_duplicate`。
- `merge_to_core` 追加/更新 `lead_sources`，并写 `review_logs`。

#### 第二轮：实现、测试和风控评审

评审结论：通过，存在真实数据库连接环境残留验证项。

发现项：

- 重复处理必须可人工 dismiss 或 mark duplicate，不能自动删除。
- 移动端需要把重复信号显示在列表和详情，不应隐藏在 API 内。
- 当前 Codex 沙箱无法连接真实 PostgreSQL，接口级真实写入验证未完成。

修正结果：

- 新增 `duplicates/resolve` 的 `merge_to_core`、`mark_duplicate`、`dismiss` 三种人工处理动作。
- 移动端列表 `riskMarkers` 增加重复标记，详情页增加“重复建议”区块并阻断强重复晋级。
- 将真实库验证阻塞原因记录为残留项。
