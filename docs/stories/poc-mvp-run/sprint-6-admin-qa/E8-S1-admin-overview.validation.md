# E8-S1 Validation：后台总览

Story：`docs/stories/sprint-6-admin-qa/E8-S1-admin-overview.md`

## TDD 记录

- Red：`PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_overview_api.py`
  - 初始在沙箱内被 PostgreSQL 网络权限拦截；随后用外部执行连接真实 PostgreSQL 验证。
- Red：`npm --prefix apps/admin run test -- adminOverview.test.mjs`
  - 初始失败：`apps/admin/src/services/adminOverview.js` 不存在。
- Green：补齐 `GET /dashboard/admin-overview`、schema/service/API、admin view model、seed 数据和总览页面后，专项测试通过。

## 验收清单

- [x] 实现后台总览页。
- [x] 展示候选线索数、B/C 级线索数、回复率、SLA 风险。
- [x] 展示渠道产出表。
- [x] 展示今日运营、客服、销售队列。
- [x] 展示风险事件和阻断任务。
- [x] 支持跳转到渠道、触达、审计页面。
- [x] 风险事件必须可见。
- [x] 管理者能看到阻断任务原因。

## 验证命令

- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_overview_api.py`
  - 结果：`1 passed, 10 warnings`
- `npm --prefix apps/admin run test -- adminOverview.test.mjs`
  - 结果：`12 passed`
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_overview_api.py apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_outreach_sla_dashboard_api.py apps/api/tests/test_roi_metrics_api.py`
  - 结果：`8 passed, 123 warnings`
- `npm --prefix apps/admin run test`
  - 结果：`12 passed`
- `npm --prefix apps/admin run check:syntax`
  - 结果：通过
- `python -m compileall apps/api/app`
  - 结果：通过
- `npm --prefix apps/mobile run test`
  - 结果：`28 passed`

## 评审记录

### 第一轮评审

- 结论：发现 1 个产品验收细节问题，修复后复测通过。
- 发现项：后台总览展示了队列和风险，但侧边栏还没有形成可点击跳转入口。
- 修正结果：侧边栏改为锚点导航，可跳转到总览、渠道、队列、审计/阻断区域。
- 复测：admin 全量测试通过。

### 第二轮评审

- 结论：未发现新增实质阻塞问题。
- 复核点：风险事件可见、阻断原因可见、勿扰客户不进入团队队列、High/Forbidden 不进入可投入建议、C 级合规护栏未被绕过。

## 残留风险

- 当前后台仍以静态 seed 数据渲染首屏，已提供 `fetchAdminOverview` 契约；真实接口联调和多页面路由可在 E8 后续 Story 中继续。
- 现有测试仍有 `datetime.utcnow()` 弃用警告，属于既有技术债，不影响 E8-S1 验收。
