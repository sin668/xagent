# E7-S3 Validation：ROI 基础指标

Story：`docs/stories/sprint-6-admin-qa/E7-S3-basic-roi-metrics.md`

## TDD 记录

- Red：`PYTHONPATH=apps/api pytest -q apps/api/tests/test_roi_metrics_api.py`
  - 初始失败：`RoiCostEntry` 模型不存在。
- Red：`node --test apps/admin/tests/roiMetrics.test.mjs`
  - 初始失败：`apps/admin/src/services/roiMetrics.js` 不存在。
- Green：补齐 ROI 成本模型、迁移、API/service/schema、admin ROI view model 后，专项测试通过。
- 补充 Red/Green：新增渠道 ROI 分母断言，先失败后修复。
- 补充 Red/Green：新增成本录入缺失人工单价返回 400 断言，先失败后修复。

## 验收清单

- [x] 记录人工时间。
- [x] 记录 AI/API 成本。
- [x] 记录工具成本。
- [x] 展示每条有效线索成本。
- [x] 展示每条回复成本。
- [x] MVP 阶段展示每个销售机会成本。
- [x] 成本口径明确。
- [x] ROI 不作为绕过合规限制的理由。

## 验证命令

- `cd apps/api && alembic upgrade head`
  - 结果：通过，已应用 `20260528_0007`。
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_roi_metrics_api.py`
  - 结果：`3 passed, 53 warnings`
- `npm --prefix apps/admin run test`
  - 结果：`10 passed`
- `npm --prefix apps/admin run check:syntax`
  - 结果：通过
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_roi_metrics_api.py apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_outreach_sla_dashboard_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_compliance_review_api.py`
  - 结果：`13 passed, 139 warnings`
- `python -m compileall apps/api/app`
  - 结果：通过
- `npm --prefix apps/mobile run test`
  - 结果：`28 passed`

## 评审记录

### 第一轮评审

- 结论：发现 1 个 ROI 口径问题，修复后复测通过。
- 发现项：`channel` 过滤只过滤成本，没有过滤有效线索和回复分母，可能误导单渠道投入判断。
- 修正结果：渠道过滤同步作用于成本、有效线索和回复分母；无渠道来源分母时成本单项仍展示，但人均成本为 `null`。
- 复测：ROI 后端专项测试通过，admin 全量测试通过。

### 第二轮评审

- 结论：发现 1 个 API 边界问题，修复后复测通过。
- 发现项：人工成本缺少工时或小时单价时由服务层异常冒泡。
- 修正结果：API 捕获 `ValueError` 并返回 400，错误信息说明人工成本字段要求。
- 复测：ROI 后端专项测试通过。

### 补充收口复核

- 结论：未发现新增实质阻塞问题。
- 复核点：成本口径、三类成本指标、渠道过滤、合规护栏、无自动触达动作、回归测试。

## 残留风险

- MVP 阶段销售机会按 C 级客户数统计，尚未做完整成交漏斗或财务模型，符合本 Story 非目标。
- 现有测试仍有 `datetime.utcnow()` 弃用警告，属于既有技术债，不影响 E7-S3 验收。
