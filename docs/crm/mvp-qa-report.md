# 海外车辆采购 AI 获客系统 MVP 端到端 QA 报告

生成日期：2026-05-28  
范围：Prompt 12，基于全部 MVP Story、总方案、现有 API、移动端、管理后台与 PoC 校验脚本执行端到端 QA。

## 结论

结论：Go，允许进入 MVP 试运行。

依据：

- 核心 API 测试通过，覆盖真实 PostgreSQL 与 Redis 环境。
- 移动端工作台关键规则通过。
- 管理后台总览、渠道风险、同步审计和 ROI 指标测试通过。
- PoC CSV 校验脚本测试通过。
- 未发现会绕过勿扰、High/Forbidden 阻断、C 级报价前合规复核、AI 审计留痕的阻塞问题。

## 验证命令

| 验证项 | 命令 | 结果 |
|---|---|---|
| API 全量测试 | `PYTHONPATH=apps/api pytest -q apps/api/tests` | `63 passed, 280 warnings` |
| API 编译 | `python -m compileall apps/api/app` | 通过 |
| Admin 全量测试 | `npm --prefix apps/admin run test` | `18 passed` |
| Admin 语法检查 | `npm --prefix apps/admin run check:syntax` | 通过 |
| Mobile 全量测试 | `npm --prefix apps/mobile run test` | `28 passed` |
| PoC CSV 校验脚本 | `PYTHONPATH=. pytest -q tests/scripts/poc/test_validate_leads.py` | `6 passed` |

## 端到端验收矩阵

| 要求 | 状态 | 证据 |
|---|---|---|
| 采集、清洗、复核、交付、触达、勿扰、合规复核、仪表盘流程 | 通过 | API 全量测试、Mobile 全量测试、Admin 全量测试 |
| 飞书数据同步到 PostgreSQL | 通过 | `test_feishu_sync_service.py`、`test_integration_postgres_redis.py` |
| CSV 校验、去重和失败案例统计 | 通过 | `tests/scripts/poc/test_validate_leads.py` |
| B 级线索 48 小时 SLA | 通过 | `test_outreach_sla_dashboard_api.py`、`outreachSlaDashboard.test.mjs` |
| C 级线索 24 小时 SLA | 通过 | `test_outreach_sla_dashboard_api.py`、`outreachSlaDashboard.test.mjs` |
| 勿扰客户不会再次进入触达 | 通过 | `test_customer_dnc_api.py`、`test_customer_dnc_service.py`、Mobile tests |
| 客户拒绝后联动勿扰 | 通过 | `test_outreach_records_api.py`、`test_customer_dnc_service.py` |
| High/Forbidden 渠道被后端阻断 | 通过 | `test_channel_risk_api.py`、`test_channel_risk_service.py`、`test_admin_channel_risk_config_api.py` |
| AI 建议有审计记录 | 通过 | `test_channel_risk_api.py`、`test_sync_ai_audit_admin_api.py`、Admin sync audit tests |
| 被阻断任务保留清晰原因 | 通过 | `test_sync_ai_audit_admin_api.py`、`syncAiAudit.test.mjs` |
| C 级报价前合规复核生效 | 通过 | `test_compliance_review_api.py`、Mobile compliance tests |
| 未确认价格不能被 AI 当成承诺输出 | 通过 | `test_inventory_api.py`、Mobile inventory tests |
| 管理后台展示渠道、触达、SLA、ROI、风险配置、同步审计 | 通过 | Admin tests：18 passed |

## 发现项

### P0 / P1 阻塞问题

无。

### P2 非阻塞问题

1. 既有 `datetime.utcnow()` 弃用警告较多。
   - 影响：当前不影响功能验收，但后续 Python 版本升级时需要统一改为 timezone-aware UTC。
   - 建议：单独建技术债 Story，统一替换为 `datetime.now(datetime.UTC)` 或项目封装时间函数。

2. 管理后台仍以 seed 数据渲染首屏。
   - 影响：API 契约已具备，但 UI 真实联调仍需后续接入运行时数据源。
   - 建议：试运行前安排一次 admin 接口联调 Story，接入 `/dashboard/*`、`/channel-risks`、`/sync/audit-dashboard`。

3. API 集成测试曾硬编码 Alembic 版本 `20260528_0001`。
   - 处理：已修正为当前 MVP head `20260528_0008`，完整 API 测试复跑通过。
   - 建议：后续新增迁移时同步更新或改为读取 Alembic head 的动态断言。

## 风控确认

- 未发现自动社交私信、自动加好友、登录后批量采集或反爬规避能力。
- High/Forbidden 渠道不可进入自动任务。
- 勿扰客户不进入触达队列，拒绝触达可联动勿扰。
- C 级线索报价/合同前合规复核仍生效。
- AI 输出和阻断原因保留审计日志。
- ROI 指标不作为绕过合规限制的理由。

## Go / No-Go

结论：Go。

试运行建议：

- 先以 Low/Medium 风险渠道继续小批量试运行。
- Admin 真实接口联调后再给运营/销售团队正式使用。
- 保留人工复核节点，不开放任何自动私信、自动加好友或高风险自动采集能力。
