# Story P1-E3-S1：实现 staging 复核列表与筛选

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P1-E3 staging 复核队列

## 用户故事

作为线索运营，我希望按待复核、B/C、High 二次复核、缺联系方式、Watch 等视图查看 staging 线索。

## 业务价值

提升人工复核效率，优先处理最可能进入 core 的线索。

## 依赖

- P1-E1-S4

## 实现范围

- 新增 staging 列表 API 筛选。
- 支持 review_status、recommended_grade、queue_status、source_risk_level、has_contact、requires_secondary_verification。
- 前端实现复核队列页面。

## 数据/API 影响

- 新增或扩展 `/staging-leads` API。
- 管理后台和移动端线索复核池对接。

## 验收标准

- 可筛选待复核线索。
- 可筛选 High 二次复核线索。
- 可筛选 Invalid/Watch。
- 列表展示来源、风险、推荐等级、联系方式状态和证据状态。

## 非目标

- 不实现批量自动晋级 core。

## 风控检查

- High/Watch/Invalid 在列表中必须有明显风险标记。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/app/services/staging_leads.py`
- `apps/api/app/schemas/staging_leads.py`
- `apps/api/app/api/staging_leads.py`
- `apps/api/tests/test_staging_review_filters.py`
- `apps/mobile/src/services/leadPool.js`
- `apps/mobile/src/services/apiAdapters.js`
- `apps/mobile/src/pages/leads/index.vue`
- `apps/mobile/tests/leadPool.test.mjs`
- `apps/mobile/tests/apiAdapters.test.mjs`
- `docs/stories/phase-1-small-run/P1-E3-S1-staging-review-list-filters.md`
- `_bmad-output/implementation-artifacts/codex-p1-e3-s1-执行结果.md`

### 验收结果

- `/staging-leads` 支持 `review_status`、`recommended_grade`、`queue_status`、`source_risk_level`、`has_contact`、`requires_secondary_verification` 筛选。
- staging 列表响应新增 `source_url`、`source_risk_level`、`has_contact`、`evidence_status`、`risk_markers`、`requires_secondary_verification`。
- 可筛选待复核线索。
- 可筛选 High 二次复核线索。
- 可筛选 Invalid/Watch。
- 列表展示来源、风险、推荐等级、联系方式状态和证据状态。
- 移动端线索池已从 `/staging-leads` 读取 staging 复核队列。
- 移动端筛选视图对齐原型：待复核、B/C、High 二次、缺联系方式、Watch/Invalid。
- High/Watch/Invalid 在卡片中通过风险等级、等级标签和 `risk_markers` 明显标记。
- 未实现批量自动晋级 core。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_review_filters.py -q`：6 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q`：69 passed。
- `npm --prefix apps/mobile test`：42 passed。
- `source ~/.zshrc && nvm use v22.22.0 && npm --prefix apps/mobile run build:h5`：Build complete。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0016 (head)`。

### 风控结果

- High 二次复核、Watch、Invalid、缺联系方式、缺证据都会生成列表风险标记。
- Watch/Invalid 仍由 staging queue 规则保持 `not_eligible`，不进入触达队列。
- 本 Story 未新增任何自动晋级 core 或自动触达能力。
