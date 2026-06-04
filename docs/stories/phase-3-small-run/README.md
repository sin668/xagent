# 第三阶段小范围运行 Story 文件

来源：

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`

执行原则：

- 每次只执行一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 每个 Story 完成后必须执行两轮独立评审。
- 必须执行必要的前后端真实联调，不允许只验证 seed 静态页面。

通用风控边界：

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- Forbidden 来源不得作为客户晋级关键来源。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级客户报价、合同、付款、物流、清关、交付周期等动作前必须合规复核。
- Agent 不得自动晋级客户、自动归并客户、自动恢复 Invalid、自动触达客户。

## Epic 总览

| Epic ID | Epic | Story 数 | 目标 |
|---|---|---:|---|
| P3-E1 | 第三阶段数据底座 | 5 | 建立线索补全、清洗、客户意向和跟进的数据底座。 |
| P3-E2 | 线索完善与字段级采纳 | 5 | 实现线索深挖触发、字段级采纳、人工补录和退出动作。 |
| P3-E3 | 客户晋级服务 | 4 | 实现满足准入条件后的人工客户晋级和客户状态基础。 |
| P3-E4 | Watch/Invalid 清洗建议 | 4 | 实现 Watch/Invalid 清洗建议查询、确认、执行和指标基础。 |
| P3-E5 | 独立 Agent 项目与 LangGraph 试点 | 5 | 新建独立 Agent 项目，局部试点 LangGraph 深挖和清洗流程。 |
| P3-E6 | 客户工作台 API | 5 | 实现客户工作台、客户详情、意向车型、跟进记录和状态 API。 |
| P3-E7 | 移动端客户工作台 | 6 | 实现移动端线索完善、清洗建议、客户工作台、客户详情和跟进页面。 |
| P3-E8 | 指标与风控看板 | 3 | 实现第三阶段指标、风控看板和复盘模板。 |
| P3-E9 | 权限、合规与审计强化 | 4 | 强化最小权限、合规硬阻断、审计事件和端到端验收。 |

## Story 清单

### P3-E1：第三阶段数据底座

- `P3-E1-S1` [创建 `lead_enrichment_results` 数据表、模型和 schema](P3-E1-S1-lead-enrichment-results-data-model.md)（Sprint 1，P0）
- `P3-E1-S2` [创建 `lead_enrichment_field_candidates` 字段级候选表、模型和 schema](P3-E1-S2-lead-enrichment-field-candidates-data-model.md)（Sprint 1，P0）
- `P3-E1-S3` [创建 `lead_cleanup_runs` 和 `lead_cleanup_suggestions` 数据模型](P3-E1-S3-lead-cleanup-data-model.md)（Sprint 1，P0）
- `P3-E1-S4` [创建客户意向车型和客户跟进记录数据模型](P3-E1-S4-customer-intents-followups-data-model.md)（Sprint 1，P0）
- `P3-E1-S5` [第三阶段 migration 链路和模型契约测试](P3-E1-S5-phase3-migration-contract-tests.md)（Sprint 1，P0）

### P3-E2：线索完善与字段级采纳

- `P3-E2-S1` [实现触发深挖线索任务 API 和配额校验](P3-E2-S1-create-enrichment-run-api.md)（Sprint 2，P0）
- `P3-E2-S2` [实现线索补全结果和字段候选查询 API](P3-E2-S2-query-enrichment-results-api.md)（Sprint 2，P0）
- `P3-E2-S3` [实现字段级采纳、修改后采纳和拒绝 API](P3-E2-S3-field-candidate-review-api.md)（Sprint 2，P0）
- `P3-E2-S4` [实现人工补录 API](P3-E2-S4-manual-enrichment-api.md)（Sprint 2，P0）
- `P3-E2-S5` [实现线索调整等级、Watch/Invalid 和放弃动作 API](P3-E2-S5-lead-exit-actions-api.md)（Sprint 2，P0）

### P3-E3：客户晋级服务

- `P3-E3-S1` [实现客户晋级最低准入校验服务](P3-E3-S1-promotion-eligibility-service.md)（Sprint 3，P0）
- `P3-E3-S2` [实现手动准入并晋级客户 API](P3-E3-S2-promote-staging-lead-to-customer-api.md)（Sprint 3，P0）
- `P3-E3-S3` [客户晋级审计和勿扰硬门禁](P3-E3-S3-promotion-audit-and-dnc-guards.md)（Sprint 3，P0）
- `P3-E3-S4` [实现客户分配和状态流转基础服务](P3-E3-S4-customer-assignment-status-service.md)（Sprint 3，P1）

### P3-E4：Watch/Invalid 清洗建议

- `P3-E4-S1` [实现清洗建议列表、详情和筛选 API](P3-E4-S1-cleanup-suggestions-query-api.md)（Sprint 4，P0）
- `P3-E4-S2` [实现清洗建议人工确认/拒绝 API](P3-E4-S2-cleanup-suggestion-review-api.md)（Sprint 4，P0）
- `P3-E4-S3` [实现清洗建议执行 API](P3-E4-S3-cleanup-suggestion-execute-api.md)（Sprint 4，P0）
- `P3-E4-S4` [清洗审计和基础指标口径](P3-E4-S4-cleanup-audit-and-metrics-foundation.md)（Sprint 4，P1）

### P3-E5：独立 Agent 项目与 LangGraph 试点

- `P3-E5-S1` [新建独立 Agent 项目并接入 LangGraph 基础结构](P3-E5-S1-agent-project-scaffold-langgraph.md)（Sprint 5，P0）
- `P3-E5-S2` [定义 Agent 项目与 apps/api 的输入输出协议](P3-E5-S2-agent-api-adapter-contract.md)（Sprint 5，P0）
- `P3-E5-S3` [实现 Deep Enrichment LangGraph 图流程](P3-E5-S3-deep-enrichment-graph.md)（Sprint 5，P1）
- `P3-E5-S4` [实现 Lead Cleanup LangGraph 图流程](P3-E5-S4-cleanup-graph.md)（Sprint 5，P1）
- `P3-E5-S5` [Agent 项目与 apps/api 任务审计联调验证](P3-E5-S5-agent-runtime-integration-verification.md)（Sprint 5，P1）

### P3-E6：客户工作台 API

- `P3-E6-S1` [实现客户工作台列表 API](P3-E6-S1-customers-workbench-list-api.md)（Sprint 6，P0）
- `P3-E6-S2` [实现客户详情聚合 API](P3-E6-S2-customer-detail-aggregate-api.md)（Sprint 6，P0）
- `P3-E6-S3` [实现客户意向车型 CRUD API](P3-E6-S3-customer-vehicle-intents-api.md)（Sprint 6，P1）
- `P3-E6-S4` [实现客户跟进记录 CRUD API](P3-E6-S4-customer-followups-api.md)（Sprint 6，P1）
- `P3-E6-S5` [客户分配、状态流转和合规硬门禁 API](P3-E6-S5-customer-assignment-compliance-guards-api.md)（Sprint 6，P1）

### P3-E7：移动端客户工作台

- `P3-E7-S1` [移动端线索详情新增完善区](P3-E7-S1-mobile-lead-enrichment-section.md)（Sprint 7，P1）
- `P3-E7-S2` [移动端清洗建议队列页面](P3-E7-S2-mobile-cleanup-suggestions-page.md)（Sprint 7，P1）
- `P3-E7-S3` [移动端客户工作台页面](P3-E7-S3-mobile-customers-workbench-page.md)（Sprint 7，P1）
- `P3-E7-S4` [移动端客户详情页面](P3-E7-S4-mobile-customer-detail-page.md)（Sprint 7，P1）
- `P3-E7-S5` [移动端客户跟进记录页面](P3-E7-S5-mobile-customer-followups-page.md)（Sprint 7，P1）
- `P3-E7-S6` [移动端第三阶段前后端联调验收](P3-E7-S6-mobile-phase3-e2e-verification.md)（Sprint 7，P1）

### P3-E8：指标与风控看板

- `P3-E8-S1` [第三阶段指标服务和口径实现](P3-E8-S1-phase3-metrics-service.md)（Sprint 8，P1）
- `P3-E8-S2` [管理后台第三阶段指标与风控看板](P3-E8-S2-admin-phase3-dashboard.md)（Sprint 8，P2）
- `P3-E8-S3` [第三阶段 Go/重跑/暂停复盘报告模板](P3-E8-S3-phase3-go-no-go-report.md)（Sprint 8，P2）

### P3-E9：权限、合规与审计强化

- `P3-E9-S1` [最小角色权限与关键动作后端守卫](P3-E9-S1-minimal-role-permission-guards.md)（Sprint 9，P1）
- `P3-E9-S2` [第三阶段合规硬阻断规则统一服务](P3-E9-S2-phase3-compliance-hard-blocks.md)（Sprint 9，P0）
- `P3-E9-S3` [第三阶段审计事件统一落库](P3-E9-S3-phase3-audit-events.md)（Sprint 9，P1）
- `P3-E9-S4` [第三阶段端到端验收与归档](P3-E9-S4-phase3-e2e-verification-archive.md)（Sprint 9，P1）

## 建议执行顺序

1. 先执行 P3-E1 全部数据底座 Story。
2. 再执行 P3-E2 和 P3-E3，打通线索完善到客户晋级闭环。
3. 同步执行 P3-E4，建立 Watch/Invalid 清洗建议闭环。
4. 再执行 P3-E5，局部试点 LangGraph 新 Agent 项目。
5. 再执行 P3-E6 和 P3-E7，完成客户工作台 API 与移动端联调。
6. 最后执行 P3-E8 和 P3-E9，完成指标、合规、审计和端到端验收。
