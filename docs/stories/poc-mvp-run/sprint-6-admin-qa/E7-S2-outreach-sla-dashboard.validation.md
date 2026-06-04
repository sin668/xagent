# E7-S2 Validation：触达与 SLA 仪表盘

Story：`docs/stories/sprint-6-admin-qa/E7-S2-outreach-sla-dashboard.md`

## TDD 记录

- Red：`PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_sla_dashboard_api.py`
  - 初始失败：`/dashboard/outreach-sla` 返回 404。
- Red：`node --test apps/admin/tests/outreachSlaDashboard.test.mjs`
  - 初始失败：`apps/admin/src/services/outreachSlaDashboard.js` 不存在。
- Green：补齐后端 SLA 统计、schema、API、admin SLA view model 和后台页面区块后，专项测试通过。
- 补充 Red/Green：新增渠道过滤应作用于待处理队列的断言，先失败后修复。

## 验收清单

- [x] 统计已触达数、回复数、回复率。
- [x] 定义 B 级 48 小时 SLA。
- [x] 定义 C 级 24 小时 SLA。
- [x] 展示超时数量和待处理队列。
- [x] 支持按负责人、等级、渠道过滤。
- [x] 生成 SLA 风险提醒。
- [x] 勿扰客户不计入待触达 SLA。
- [x] C 级线索区分合规复核等待时间。

## 验证命令

- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_sla_dashboard_api.py`
  - 结果：`2 passed, 25 warnings`
- `npm --prefix apps/admin run test`
  - 结果：`7 passed`
- `npm --prefix apps/admin run check:syntax`
  - 结果：通过
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_sla_dashboard_api.py apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_compliance_review_api.py`
  - 结果：`13 passed, 103 warnings`
- `python -m compileall apps/api/app`
  - 结果：通过
- `npm --prefix apps/mobile run test`
  - 结果：`28 passed`

## 评审记录

### 第一轮评审

- 结论：发现 1 个需求口径问题，修复后复测通过。
- 发现项：`channel` 过滤只影响触达统计，没有影响待处理 SLA 队列。
- 修正结果：渠道过滤同步作用于待处理客户队列，按已有触达记录渠道筛选客户。
- 复测：后端专项测试通过，admin 全量测试通过。

### 第二轮评审

- 结论：发现 1 个接口边界问题，修复后复测通过。
- 发现项：`channel` 非法值会进入服务层枚举转换，应该在 API 查询参数层校验。
- 修正结果：`/dashboard/outreach-sla` 的 `channel` 查询参数增加允许值校验。
- 复测：后端专项测试通过，Python 编译通过。

### 补充收口复核

- 结论：未发现新增实质阻塞问题。
- 复核点：回复率、B/C SLA、勿扰排除、C 级合规等待、负责人/等级/渠道过滤、后台风险队列展示、无自动触达动作。

## 残留风险

- SLA 计时当前使用 `Customer.updated_at` 作为进入承接队列时间，后续如果需要更精确的交付时间，可在交付 Story 中补充独立字段。
- 现有测试仍有 `datetime.utcnow()` 弃用警告，属于既有技术债，不影响 E7-S2 验收。
