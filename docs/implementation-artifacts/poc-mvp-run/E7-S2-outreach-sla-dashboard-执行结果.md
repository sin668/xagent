# E7-S2 触达与 SLA 仪表盘执行结果

## Story

- `docs/stories/sprint-6-admin-qa/E7-S2-outreach-sla-dashboard.md`
- 状态：Done

## 实现范围

- 后端新增 `GET /dashboard/outreach-sla`。
- 支持统计：
  - 已触达数
  - 回复数
  - 回复率
  - 待处理数
  - 超时数
  - C 级合规等待数
  - SLA 风险数
- 支持 SLA：
  - B 级 48 小时
  - C 级 24 小时
- 支持过滤：
  - 负责人
  - 等级
  - 触达渠道
- 管理后台新增：
  - 触达与 SLA 指标卡
  - SLA 风险队列
  - admin service 与 API fetch 契约

## 合规边界

- 勿扰客户不进入待触达 SLA 队列。
- C 级未合规复核通过时展示为合规等待，不混同为普通超时。
- 未实现自动触达、自动私信、自动加好友。

## 验证结果

- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_sla_dashboard_api.py`：`2 passed, 25 warnings`
- `npm --prefix apps/admin run test`：`7 passed`
- `npm --prefix apps/admin run check:syntax`：通过
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_sla_dashboard_api.py apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_compliance_review_api.py`：`13 passed, 103 warnings`
- `python -m compileall apps/api/app`：通过
- `npm --prefix apps/mobile run test`：`28 passed`

## 评审记录

### 第一轮

- 发现项：渠道过滤未作用于 SLA 待处理队列。
- 修正：队列查询按触达记录渠道筛选客户。
- 结果：专项后端测试和 admin 测试通过。

### 第二轮

- 发现项：非法渠道值应在 API 层校验。
- 修正：`channel` 查询参数增加枚举值 pattern。
- 结果：专项后端测试和 Python 编译通过。

### 补充收口复核

- 结论：未发现新增实质阻塞问题。

## 文件清单

- `apps/api/app/api/dashboard.py`
- `apps/api/app/schemas/dashboard.py`
- `apps/api/app/services/dashboard.py`
- `apps/api/tests/test_outreach_sla_dashboard_api.py`
- `apps/admin/src/App.vue`
- `apps/admin/src/data/outreachSlaDashboardSeed.js`
- `apps/admin/src/services/outreachSlaDashboard.js`
- `apps/admin/src/styles/admin.css`
- `apps/admin/tests/outreachSlaDashboard.test.mjs`
- `docs/stories/sprint-6-admin-qa/E7-S2-outreach-sla-dashboard.md`
- `docs/stories/sprint-6-admin-qa/E7-S2-outreach-sla-dashboard.validation.md`
- `_bmad-output/implementation-artifacts/E7-S2-outreach-sla-dashboard-执行结果.md`
