# P1-E3-S4 执行结果

Story：`docs/stories/phase-1-small-run/P1-E3-S4-dedupe-merge-suggestions.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、移动端展示、测试与构建验证；真实 PostgreSQL 接口级写入验证待当前工具出网/审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划、`docs/AI协同开发执行标准.md` 和 superpowers TDD/verification 规范执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

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

## 3. 实现内容

### 3.1 后端重复信号

新增 dedupe 规则：

- 强重复：标准化客户名称 + 联系方式 hash
- 疑似重复：标准化客户名称 + 城市 + 来源域名
- 来源重复：来源 URL hash

staging list/detail 响应新增：

```text
duplicate_signals
```

### 3.2 重复候选 API

新增：

```text
GET /staging-leads/{lead_id}/duplicates
POST /staging-leads/{lead_id}/duplicates/resolve
```

人工处理动作：

- `merge_to_core`
- `mark_duplicate`
- `dismiss`

### 3.3 晋级阻断

`promote_staging_lead_to_core` 在准入闸门通过后继续检查强重复，存在强重复时阻断晋级 core。

### 3.4 证据保全

`merge_to_core` 不删除 staging 记录，不覆盖目标 customer 勿扰状态，而是追加或更新：

- `lead_sources`
- `contact_methods`
- `review_logs`

### 3.5 移动端展示

移动端列表显示：

- `强重复阻断`
- `疑似重复待复核`

移动端详情页新增“重复建议”区块。强重复会禁用底部晋级按钮并显示 `重复待处理`。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 强重复必须阻止重复晋级 | 通过 | promote 调用 `raise_if_strong_duplicate` |
| 疑似重复必须进入人工复核，不自动删除 | 通过 | `requires_manual_review` + resolve 人工动作 |
| 合并后保留所有来源证据 | 通过 | `merge_to_core` 追加/更新 `lead_sources` |
| 强重复规则 | 通过 | 标准化名称 + 联系方式 hash |
| 疑似重复规则 | 通过 | 标准化名称 + 城市 + 来源域名 |
| 来源重复规则 | 通过 | URL hash |
| staging list/detail 返回 duplicate signals | 通过 | `StagingLeadResponse.duplicate_signals` |
| 展示重复候选并允许人工处理 | 通过 | duplicates API + 移动端展示 |
| 不做复杂机器学习去重 | 通过 | 仅规则去重 |
| 不因去重丢失勿扰状态 | 通过 | 合并不修改目标 customer DNC 字段 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_dedupe_merge_suggestions.py -q
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0
npm --prefix apps/mobile test
```

结果：

- 后端失败：缺少 dedupe API 契约、重复 key 构造、重复信号和合并 payload。
- 移动端失败：列表 adapter 未消费 `duplicate_signals`，详情 view model 未阻断强重复。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_dedupe_merge_suggestions.py -q
```

结果：

```text
5 passed in 0.25s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_dedupe_merge_suggestions.py apps/api/tests/test_promote_staging_to_core.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q
```

结果：

```text
81 passed in 0.96s
```

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0
npm --prefix apps/mobile test
```

结果：

```text
46 passed
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

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260529_0016 (head)
```

## 6. 两轮独立评审

### 6.1 第一轮：需求、规则和数据保全评审

结论：通过。

发现项：

- Story 要求“来源重复：URL hash”，不能只按 URL 字符串完全相等判断。
- 强重复必须阻断 promote，不能只在列表提示。
- 合并重复时必须保留来源证据，不能通过删除 staging 或覆盖 core source 简化处理。

修正结果：

- `build_duplicate_keys` 输出 `source_url_hash`，来源重复按 hash 比对。
- `promote_staging_lead_to_core` 调用 `raise_if_strong_duplicate`。
- `merge_to_core` 追加/更新 `lead_sources`，并写 `review_logs`。

### 6.2 第二轮：实现、测试和风控评审

结论：通过，存在真实数据库连接环境残留验证项。

发现项：

- 重复处理必须可人工 dismiss 或 mark duplicate，不能自动删除。
- 移动端需要把重复信号显示在列表和详情，不应隐藏在 API 内。
- 当前 Codex 沙箱无法连接真实 PostgreSQL，接口级真实写入验证未完成。

修正结果：

- 新增 `duplicates/resolve` 的 `merge_to_core`、`mark_duplicate`、`dismiss` 三种人工处理动作。
- 移动端列表 `riskMarkers` 增加重复标记，详情页增加“重复建议”区块并阻断强重复晋级。
- 将真实库验证阻塞原因写入测试结果和执行产物。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL，重复处理 API 的真实库写入需在可出网终端复验。
- `duplicate_signals_for_lead` 当前为规则查询，适合 PoC/小范围运行；大规模运行时需要索引优化或物化重复信号。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E4-S1-channel-discovery-agent.md`
