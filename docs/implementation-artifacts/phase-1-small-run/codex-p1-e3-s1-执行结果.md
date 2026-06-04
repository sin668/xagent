# P1-E3-S1 执行结果

Story：`docs/stories/phase-1-small-run/P1-E3-S1-staging-review-list-filters.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、移动端对接与可用验证；真实 PostgreSQL 接口数据验证待当前工具出网/审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

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

## 3. 实现内容

### 3.1 后端 staging 筛选

`GET /staging-leads` 新增筛选参数：

- `review_status`
- `recommended_grade`
- `queue_status`
- `source_risk_level`
- `has_contact`
- `requires_secondary_verification`
- `limit`

`StagingLeadService.list_staging_leads` 支持 join `candidate_urls`，用于按来源风险与二次复核状态筛选。

### 3.2 列表展示字段

`StagingLeadResponse` 新增：

- `source_url`
- `source_risk_level`
- `requires_secondary_verification`
- `has_contact`
- `evidence_status`
- `risk_markers`

`risk_markers` 覆盖：

- `High 二次复核`
- `Watch 不进入触达`
- `Invalid 不进入触达`
- `缺联系方式`
- `缺来源证据`

### 3.3 移动端线索复核池

移动端 `pages/leads/index.vue` 改为读取：

- `GET /staging-leads?limit=100`

新增 adapter：

- `mapStagingLeadListToLeadPool`

移动端筛选视图更新为：

- 待复核
- B/C
- High 二次
- 缺联系方式
- Watch/Invalid

卡片展示继续包含来源、风险、推荐等级、联系方式/证据风险标记。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 新增 staging 列表 API 筛选 | 通过 | `/staging-leads` query 参数已扩展 |
| 支持 `review_status` | 通过 | service/API 测试覆盖 |
| 支持 `recommended_grade` | 通过 | service/API 测试覆盖，支持多值 |
| 支持 `queue_status` | 通过 | service/API 已接入 |
| 支持 `source_risk_level` | 通过 | join `candidate_urls` 筛选 |
| 支持 `has_contact` | 通过 | `StagingLeadService.has_contact` |
| 支持 `requires_secondary_verification` | 通过 | join `candidate_urls` 筛选 |
| 可筛选待复核线索 | 通过 | `review_filter_presets` 和 API query |
| 可筛选 High 二次复核线索 | 通过 | `high_secondary` preset |
| 可筛选 Invalid/Watch | 通过 | `watch_invalid` preset |
| 列表展示来源、风险、推荐等级、联系方式状态和证据状态 | 通过 | response 字段与移动端 adapter |
| 前端实现复核队列页面 | 通过 | 移动端线索池对接 `/staging-leads` |
| 不实现批量自动晋级 core | 通过 | 未新增晋级 core 逻辑 |
| High/Watch/Invalid 有明显风险标记 | 通过 | `risk_markers` + 卡片标签 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_review_filters.py -q
node apps/mobile/tests/leadPool.test.mjs
node apps/mobile/tests/apiAdapters.test.mjs
```

结果：

- 后端测试失败，原因是筛选参数、响应字段、`has_contact`、`risk_markers` 等尚未实现。
- 移动端测试失败，原因是线索池仍是旧的 B/C/超时/勿扰筛选，且没有 staging adapter。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_review_filters.py -q
```

结果：

```text
6 passed in 0.19s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py apps/api/tests/test_staging_review_filters.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q
```

结果：

```text
69 passed in 0.28s
```

```bash
npm --prefix apps/mobile test
```

结果：

```text
42 passed
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

### 6.1 第一轮：产品与信息架构评审

结论：通过。

发现项：

- 原移动端线索池仍是客服/销售线索池视角，不符合 staging 复核池的“待复核、B/C、High 二次、缺联系方式、Watch/Invalid”视图。
- 后端响应缺少来源风险、联系方式状态和证据状态，前端只能猜。
- `source_risk_level` 不能从 staging 本表直接取，需要关联 candidate URL。

修正结果：

- 移动端筛选视图改为复核池视角。
- 后端 response 增加 `source_url`、`source_risk_level`、`has_contact`、`evidence_status`、`risk_markers`。
- service 查询 join `candidate_urls`，支持来源风险和二次复核筛选。

### 6.2 第二轮：风控与队列边界评审

结论：通过，存在一个环境残留验证项。

发现项：

- High、Watch、Invalid 必须在列表上直接可见，不能只藏在详情页。
- 缺联系方式、缺证据会影响是否可进入触达/晋级，应在列表层暴露。
- 当前工具环境仍无法连接真实 PostgreSQL 做接口级数据验证。

修正结果：

- `risk_markers` 明确输出 High 二次复核、Watch/Invalid 不触达、缺联系方式、缺来源证据。
- 移动端卡片直接显示 `risk_markers`。
- 在执行结果中记录真实库接口验证待复验。

## 7. 残留风险

- 真实 PostgreSQL 环境下的 `/staging-leads` 数据查询未能在当前工具环境完成，需要在可出网环境复验。
- 管理后台当前仍以总览队列为主，后续可在独立后台 Story 中补齐完整 staging review table。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E3-S2-staging-lead-detail-evidence.md`
