# E8-S2 渠道风险配置后台执行结果

## Story

- `docs/stories/sprint-6-admin-qa/E8-S2-admin-channel-risk-config.md`
- 状态：Done

## 实现范围

- 新增 Alembic 迁移：`20260528_0008_add_channel_risk_updated_by.py`
- 扩展渠道风险规则：
  - `updated_by`
  - `updated_at` 响应字段
- 扩展后端接口：
  - `GET /channel-risks`
  - `PUT /channel-risks/{channel_name}`
  - `POST /channel-risks/evaluate-ai-task`
- 管理后台新增渠道风险配置区块，展示：
  - 渠道名称和类型
  - 风险等级
  - 允许动作
  - 禁止动作
  - 政策来源
  - 变更人
  - 自动任务状态与阻断原因

## 合规边界

- High/Forbidden 渠道强制 `collection_allowed = false`。
- High/Forbidden 渠道强制 `ai_processing_allowed = false`。
- Forbidden 行为不能通过前端 payload 绕过。
- 被阻断的 AI 任务继续写入审计日志和 `risk_block_reason`。
- 本 Story 不实现自动抓取平台政策更新。

## 验证结果

- `cd apps/api && alembic upgrade head`：通过，已应用 `20260528_0008`
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_channel_risk_config_api.py`：`2 passed, 3 warnings`
- `npm --prefix apps/admin run test -- channelRiskConfig.test.mjs`：`15 passed`
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_channel_risk_config_api.py apps/api/tests/test_channel_risk_api.py apps/api/tests/test_channel_risk_service.py apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_admin_overview_api.py`：`13 passed, 62 warnings`
- `npm --prefix apps/admin run test`：`15 passed`
- `npm --prefix apps/admin run check:syntax`：通过
- `python -m compileall apps/api/app`：通过
- `npm --prefix apps/mobile run test`：`28 passed`

## 评审记录

### 第一轮

- 发现项：旧调用未传 `updated_by` 时可能没有操作者留痕。
- 修正：服务层缺省记录为 `unknown`。
- 结果：后端专项测试与 admin 全量测试通过。

### 第二轮

- 结论：未发现新增实质阻塞问题。
- 复核点：风险等级维护、允许/禁止动作维护、政策来源维护、操作者/时间留痕、Forbidden 前端绕过防护、High/Forbidden 自动任务阻断和阻断原因展示。

## 文件清单

- `apps/api/app/api/channel_risk.py`
- `apps/api/app/models/channel_risk_rule.py`
- `apps/api/app/schemas/channel_risk.py`
- `apps/api/app/services/channel_risk.py`
- `apps/api/alembic/versions/20260528_0008_add_channel_risk_updated_by.py`
- `apps/api/tests/test_admin_channel_risk_config_api.py`
- `apps/admin/package.json`
- `apps/admin/src/App.vue`
- `apps/admin/src/data/channelRiskConfigSeed.js`
- `apps/admin/src/services/channelRiskConfig.js`
- `apps/admin/src/styles/admin.css`
- `apps/admin/tests/channelRiskConfig.test.mjs`
- `docs/stories/sprint-6-admin-qa/E8-S2-admin-channel-risk-config.md`
- `docs/stories/sprint-6-admin-qa/E8-S2-admin-channel-risk-config.validation.md`
- `_bmad-output/implementation-artifacts/E8-S2-admin-channel-risk-config-执行结果.md`
