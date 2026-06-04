# E8-S2 Validation：渠道风险配置后台

Story：`docs/stories/sprint-6-admin-qa/E8-S2-admin-channel-risk-config.md`

## TDD 记录

- Red：`PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_channel_risk_config_api.py`
  - 初始失败：响应缺少 `updated_by`；Forbidden 渠道可被前端 payload 设置 `collection_allowed = true`。
- Red：`npm --prefix apps/admin run test -- channelRiskConfig.test.mjs`
  - 初始失败：`apps/admin/src/services/channelRiskConfig.js` 不存在。
- Green：补齐 `updated_by` 字段迁移、API/schema/service、Forbidden 强制阻断、admin 风险配置 view model 和 seed 数据后，专项测试通过。

## 验收清单

- [x] 实现渠道风险配置列表。
- [x] 支持查看所有渠道及风险等级。
- [x] 支持维护允许动作、禁止动作和政策来源。
- [x] 配置变更记录操作人和时间。
- [x] High/Forbidden 渠道被自动任务阻断。
- [x] 展示阻断原因。
- [x] 修改风险等级需留痕。
- [x] Forbidden 行为不能通过前端绕过。

## 验证命令

- `cd apps/api && alembic upgrade head`
  - 结果：通过，已应用 `20260528_0008`。
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_channel_risk_config_api.py`
  - 结果：`2 passed, 3 warnings`
- `npm --prefix apps/admin run test -- channelRiskConfig.test.mjs`
  - 结果：`15 passed`
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_admin_channel_risk_config_api.py apps/api/tests/test_channel_risk_api.py apps/api/tests/test_channel_risk_service.py apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_admin_overview_api.py`
  - 结果：`13 passed, 62 warnings`
- `npm --prefix apps/admin run test`
  - 结果：`15 passed`
- `npm --prefix apps/admin run check:syntax`
  - 结果：通过
- `python -m compileall apps/api/app`
  - 结果：通过
- `npm --prefix apps/mobile run test`
  - 结果：`28 passed`

## 评审记录

### 第一轮评审

- 结论：发现 1 个留痕完整性问题，修复后复测通过。
- 发现项：旧调用如果未传 `updated_by`，风险规则变更仍可能没有操作者记录。
- 修正结果：服务层将缺省操作者记录为 `unknown`，避免空留痕。
- 复测：E8-S2 后端专项测试通过，admin 全量测试通过。

### 第二轮评审

- 结论：未发现新增实质阻塞问题。
- 复核点：Forbidden 前端绕过、High/Forbidden 自动任务阻断、阻断原因审计、允许/禁止动作与政策来源可维护、移动端触达风险规则未回归。

## 残留风险

- 当前管理后台仍以 seed 数据渲染首屏，已提供 `fetchChannelRiskRules` 与 `updateChannelRiskRule` 契约；真实接口联调可在 E8 后续 Story 或统一联调中推进。
- 现有测试仍有 `datetime.utcnow()` 弃用警告，属于既有技术债，不影响 E8-S2 验收。
