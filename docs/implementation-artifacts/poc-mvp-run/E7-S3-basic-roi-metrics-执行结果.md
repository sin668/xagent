# E7-S3 ROI 基础指标执行结果

## Story

- `docs/stories/sprint-6-admin-qa/E7-S3-basic-roi-metrics.md`
- 状态：Done

## 实现范围

- 新增 ROI 成本表：`roi_cost_entries`
- 新增 Alembic 迁移：`20260528_0007_add_roi_cost_entries.py`
- 新增后端接口：
  - `POST /dashboard/roi-costs`
  - `GET /dashboard/roi-metrics`
- 支持记录：
  - 人工时间和小时单价
  - AI/API 成本
  - 工具成本
- 支持展示：
  - 每条有效线索成本
  - 每条回复成本
  - 每个销售机会成本
- 管理后台新增 ROI 基础指标区块。

## 合规边界

- ROI 只作为经营判断参考。
- ROI 不能作为绕过 High/Forbidden、勿扰、C 级报价前合规复核的理由。
- 未实现完整财务模型，未实现销售奖金或绩效核算。

## 验证结果

- `cd apps/api && alembic upgrade head`：通过
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_roi_metrics_api.py`：`3 passed, 53 warnings`
- `npm --prefix apps/admin run test`：`10 passed`
- `npm --prefix apps/admin run check:syntax`：通过
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_roi_metrics_api.py apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_outreach_sla_dashboard_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_compliance_review_api.py`：`13 passed, 139 warnings`
- `python -m compileall apps/api/app`：通过
- `npm --prefix apps/mobile run test`：`28 passed`

## 评审记录

### 第一轮

- 发现项：渠道过滤只作用于成本，未作用于有效线索和回复分母。
- 修正：渠道过滤同步作用于成本、有效线索和回复分母。
- 结果：ROI 后端专项测试和 admin 全量测试通过。

### 第二轮

- 发现项：成本录入缺少人工成本字段时未返回标准 400。
- 修正：API 捕获服务层校验错误并返回 400。
- 结果：ROI 后端专项测试通过。

### 补充收口复核

- 结论：未发现新增实质阻塞问题。

## 文件清单

- `apps/api/app/api/dashboard.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/models/roi_cost_entry.py`
- `apps/api/app/schemas/dashboard.py`
- `apps/api/app/services/dashboard.py`
- `apps/api/alembic/versions/20260528_0007_add_roi_cost_entries.py`
- `apps/api/tests/test_roi_metrics_api.py`
- `apps/admin/src/App.vue`
- `apps/admin/src/data/roiMetricsSeed.js`
- `apps/admin/src/services/roiMetrics.js`
- `apps/admin/src/styles/admin.css`
- `apps/admin/tests/roiMetrics.test.mjs`
- `docs/stories/sprint-6-admin-qa/E7-S3-basic-roi-metrics.md`
- `docs/stories/sprint-6-admin-qa/E7-S3-basic-roi-metrics.validation.md`
- `_bmad-output/implementation-artifacts/E7-S3-basic-roi-metrics-执行结果.md`
