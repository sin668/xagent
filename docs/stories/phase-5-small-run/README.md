# 第五阶段小范围运行 Story 文件

来源：

- `docs/brainstorm/brainstorming-session-2026-06-05-第五阶段小范围运行-Prompt与邮件自动回复知识库.md`
- `docs/product/2026-06-05-海外车辆采购AI获客系统-第五阶段小范围运行方案与产品技术设计.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `prototypes/mvp-mobile-agent/pages/email-replies.html`
- `prototypes/mvp-mobile-agent/pages/email-reply-detail.html`
- `prototypes/mvp-mobile-agent/pages/admin-prompt-governance.html`
- `prototypes/mvp-mobile-agent/pages/admin-knowledge-base.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-replies.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-quality.html`

执行原则：

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 代码实现必须使用 `superpowers:test-driven-development`；调试异常必须使用 `superpowers:systematic-debugging`；完成前必须使用 `superpowers:verification-before-completion`。
- 环境按项目约定使用 `conda activate booking-room` 和 `nvm use v22.22.0`。
- 后端、Agent、后台和移动端联调必须使用真实 API、真实 PostgreSQL 和 Redis，不允许只验证 seed 静态页面。
- 每个 Story 完成后必须执行两轮独立多维度评审，并在 Story 或执行记录中写明结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

第五阶段通用风控边界：

- `apps/api` 是唯一业务数据权威，业务 core 表写入、权限、审计、DNC/勿扰、自动发送准入、硬拦截和邮件发送提交必须由 `apps/api` 控制。
- `apps/agents` 只做编排、LLM 调用、节点追踪和结果回传，不直接写 `customers`、`contact_methods`、`lead_sources`、`knowledge_items`、`email_reply_drafts`、`outreach_records` 等业务 core 表。
- 不自动社交私信、不自动加好友、不登录后批量采集、不反爬规避、不抓取非公开数据。
- DNC/勿扰、Watch/Invalid（对外 D/E 级）、语言不确定、知识召回不足、缺少知识证据、价格/付款/合同/发票/税务/法律/交付/出口管制等场景不得自动发送。
- LLM 输出必须结构化；缺失字段输出 `Unknown`、`null` 或空数组，不得编造。
- AI 建议回复和最终发送内容必须分开保存并可审计。

## 阶段目标

第五阶段目标是把文件 Prompt、邮件自动回复内容、Q&A 知识库、pgvector 语义召回、`EMAIL_REPLY` Agent 和真实邮件发送通道串成可治理、可审计、可暂停的小范围运行闭环。

本阶段只允许在白名单客户、固定 FAQ、首次邮件触达、低风险场景，并通过后端自动发送准入与硬拦截后自动发送；其他场景必须进入人工确认。

## Epic 总览

| Epic ID | Epic | Story 数 | 目标 |
|---|---|---:|---|
| P5-E1 | 数据底座 | 6 | 建立 Prompt、邮件线程、AI 回复草稿、发送尝试和质量使用记录的数据基础。 |
| P5-E2 | Prompt 入库治理 | 6 | 把文件 Prompt 幂等迁移入库，并提供草稿、校验、发布、默认版本和回滚能力。 |
| P5-E3 | Q&A/邮件回复知识库 | 5 | 复用知识库底座管理 Q&A、邮件模板、合规话术、车型说明和流程 SOP。 |
| P5-E4 | pgvector embedding 异步 | 5 | 发布知识后异步生成向量，并支持状态、重试、过期和召回测试。 |
| P5-E5 | apps/admin 后台管理页面 | 5 | 将第五阶段原型落到后台真实页面，接入真实 API。 |
| P5-E6 | 自动回复规则与审计 | 5 | 实现自动发送准入、硬拦截、DNC/D/E 阻断、上下文构建和审计链路。 |
| P5-E7 | EMAIL_REPLY Agent | 6 | 在 `apps/agents` 新增 EMAIL_REPLY 任务流，并由 `apps/api` 通过 HTTP 集成。 |
| P5-E8 | 邮件发送通道 | 5 | 建立统一 EmailSender 适配层、发送确认、白名单自动发送、失败退信和触达历史联动。 |
| P5-E9 | 质量指标与端到端验收 | 5 | 完成 Prompt、知识、embedding、邮件回复、风险和 Go/No-Go 指标闭环。 |

## Story 清单

### P5-E1：数据底座

- `P5-E1-S1` [扩展 Prompt 模板治理字段与枚举](P5-E1-S1-prompt-template-governance-fields.md)（Sprint 1，P0）
- `P5-E1-S2` [新增待回复邮件线程与消息模型](P5-E1-S2-email-thread-message-data-model.md)（Sprint 1，P0）
- `P5-E1-S3` [新增 AI 邮件回复草稿模型](P5-E1-S3-email-reply-drafts-model.md)（Sprint 1，P0）
- `P5-E1-S4` [新增邮件发送尝试模型](P5-E1-S4-email-send-attempts-model.md)（Sprint 1，P0）
- `P5-E1-S5` [新增知识质量指标与使用记录模型](P5-E1-S5-knowledge-quality-usage-model.md)（Sprint 1，P1）
- `P5-E1-S6` [第五阶段数据 migration contract tests](P5-E1-S6-phase5-migration-contract-tests.md)（Sprint 1，P0）
### P5-E2：Prompt 入库治理

- `P5-E2-S1` [Prompt 文件解析与 hash 计算服务](P5-E2-S1-prompt-file-parser-hash-service.md)（Sprint 2，P0）
- `P5-E2-S2` [Prompt 入库迁移脚本](P5-E2-S2-prompt-import-migration-script.md)（Sprint 2，P0）
- `P5-E2-S3` [Prompt 草稿创建与编辑 API](P5-E2-S3-prompt-draft-edit-api.md)（Sprint 2，P0）
- `P5-E2-S4` [Prompt 变量、schema 与测试样例校验 API](P5-E2-S4-prompt-validation-preview-api.md)（Sprint 2，P0）
- `P5-E2-S5` [Prompt 发布、默认版本与回滚 API](P5-E2-S5-prompt-publish-default-rollback-api.md)（Sprint 2，P0）
- `P5-E2-S6` [Prompt 治理审计与权限边界](P5-E2-S6-prompt-governance-audit-permissions.md)（Sprint 2，P1）
### P5-E3：Q&A/邮件回复知识库

- `P5-E3-S1` [知识库内容类型与业务属性扩展](P5-E3-S1-knowledge-content-type-business-fields.md)（Sprint 3，P0）
- `P5-E3-S2` [Q&A 与邮件回复模板 CRUD API](P5-E3-S2-knowledge-qa-email-template-crud-api.md)（Sprint 3，P0）
- `P5-E3-S3` [知识库审核发布与下线 API](P5-E3-S3-knowledge-review-publish-archive-api.md)（Sprint 3，P0）
- `P5-E3-S4` [知识库召回过滤 API](P5-E3-S4-knowledge-retrieval-filter-api.md)（Sprint 3，P0）
- `P5-E3-S5` [知识库质量使用记录 API](P5-E3-S5-knowledge-quality-usage-api.md)（Sprint 3，P1）
### P5-E4：pgvector embedding 异步

- `P5-E4-S1` [embedding 任务状态与重试服务](P5-E4-S1-embedding-task-status-retry-service.md)（Sprint 4，P0）
- `P5-E4-S2` [发布后异步生成 pgvector embedding worker](P5-E4-S2-embedding-async-worker.md)（Sprint 4，P0）
- `P5-E4-S3` [embedding stale 与新版本处理](P5-E4-S3-embedding-stale-new-version-handling.md)（Sprint 4，P1）
- `P5-E4-S4` [RAG 召回测试 API](P5-E4-S4-rag-retrieval-test-api.md)（Sprint 4，P0）
- `P5-E4-S5` [embedding 指标与失败案例](P5-E4-S5-embedding-metrics-failed-cases.md)（Sprint 4，P1）
### P5-E5：apps/admin 后台管理页面

- `P5-E5-S1` [apps/admin Prompt 入库治理页面](P5-E5-S1-admin-prompt-governance-page.md)（Sprint 5，P0）
- `P5-E5-S2` [apps/admin Q&A 与邮件回复知识库页面](P5-E5-S2-admin-knowledge-base-page.md)（Sprint 5，P0）
- `P5-E5-S3` [apps/admin 邮件回复审核台页面](P5-E5-S3-admin-email-replies-review-page.md)（Sprint 5，P0）
- `P5-E5-S4` [apps/admin 邮件质量指标页面](P5-E5-S4-admin-email-quality-page.md)（Sprint 5，P1）
- `P5-E5-S5` [后台权限与真实 API 联调](P5-E5-S5-admin-permissions-real-api-integration.md)（Sprint 5，P0）
### P5-E6：自动回复规则与审计

- `P5-E6-S1` [自动发送准入规则服务](P5-E6-S1-auto-send-eligibility-service.md)（Sprint 6，P0）
- `P5-E6-S2` [硬拦截规则服务](P5-E6-S2-hard-block-rule-service.md)（Sprint 6，P0）
- `P5-E6-S3` [DNC 与 D/E 客户阻断集成](P5-E6-S3-dnc-de-grade-block-integration.md)（Sprint 6，P0）
- `P5-E6-S4` [AI 建议与最终发送分离审计](P5-E6-S4-ai-suggestion-final-send-audit.md)（Sprint 6，P0）
- `P5-E6-S5` [自动回复上下文构建服务](P5-E6-S5-email-reply-context-builder.md)（Sprint 6，P1）
### P5-E7：EMAIL_REPLY Agent

- `P5-E7-S1` [apps/agents EMAIL_REPLY schema 与 envelope](P5-E7-S1-email-reply-agent-schema-envelope.md)（Sprint 7，P0）
- `P5-E7-S2` [EMAIL_REPLY load_context 与 retrieve_knowledge 节点](P5-E7-S2-email-reply-load-context-retrieve-knowledge.md)（Sprint 7，P0）
- `P5-E7-S3` [EMAIL_REPLY draft_reply 与 schema validation 节点](P5-E7-S3-email-reply-draft-schema-validation.md)（Sprint 7，P0）
- `P5-E7-S4` [EMAIL_REPLY auto_send_check 与 route_decision 节点](P5-E7-S4-email-reply-auto-send-check-route.md)（Sprint 7，P0）
- `P5-E7-S5` [新增 `/agent-runs/email-reply` HTTP API](P5-E7-S5-email-reply-agent-run-http-api.md)（Sprint 7，P0）
- `P5-E7-S6` [apps/api EmailReplyAgent client 集成](P5-E7-S6-api-email-reply-agent-client-integration.md)（Sprint 7，P0）
### P5-E8：邮件发送通道

- `P5-E8-S1` [EmailSender 适配层与配置](P5-E8-S1-email-sender-adapter-config.md)（Sprint 8，P0）
- `P5-E8-S2` [发送前检查与预览 API](P5-E8-S2-email-send-preview-check-api.md)（Sprint 8，P0）
- `P5-E8-S3` [人工确认发送 API](P5-E8-S3-manual-confirm-email-send-api.md)（Sprint 8，P0）
- `P5-E8-S4` [白名单低风险自动发送 API](P5-E8-S4-whitelist-low-risk-auto-send-api.md)（Sprint 8，P0）
- `P5-E8-S5` [失败重试、退信记录与触达历史联动](P5-E8-S5-email-failure-bounce-outreach-history.md)（Sprint 8，P1）
### P5-E9：质量指标与端到端验收

- `P5-E9-S1` [Prompt、知识与 embedding 指标服务](P5-E9-S1-prompt-knowledge-embedding-metrics.md)（Sprint 9，P1）
- `P5-E9-S2` [邮件回复采纳率、编辑幅度与退信率指标](P5-E9-S2-email-reply-quality-metrics.md)（Sprint 9，P1）
- `P5-E9-S3` [第五阶段 Go/No-Go 报告 API 与文档](P5-E9-S3-phase5-go-no-go-report.md)（Sprint 9，P1）
- `P5-E9-S4` [第五阶段端到端真实联调验收](P5-E9-S4-phase5-e2e-real-integration.md)（Sprint 9，P0）
- `P5-E9-S5` [第五阶段归档与执行报告](P5-E9-S5-phase5-archive-execution-report.md)（Sprint 9，P1）

## 建议执行顺序

1. 先执行 P5-E1，建立 Prompt、邮件、回复草稿、发送记录和质量记录的数据底座。
2. 再执行 P5-E2，把文件 Prompt 幂等入库并建立草稿、校验、发布、默认版本和回滚治理。
3. 再执行 P5-E3 和 P5-E4，完成 Q&A/邮件回复知识库与 pgvector embedding 异步召回基础。
4. 再执行 P5-E5，将原型对应的后台页面接入真实 API。
5. 再执行 P5-E6，建立自动发送准入、硬拦截、DNC/D/E 阻断和审计链路。
6. 再执行 P5-E7，让 `apps/agents` 新增 `EMAIL_REPLY` Agent 并由 `apps/api` HTTP 集成。
7. 再执行 P5-E8，接入邮件发送适配层、人工确认发送、低风险自动发送和失败退信闭环。
8. 最后执行 P5-E9，完成指标、Go/No-Go 报告和端到端真实联调验收。

## 本次拆分复核记录

### 第一轮独立复核：覆盖性检查

复核维度：

- README 中 Story 链接数量。
- `docs/stories/phase-5-small-run` 目录下实际 Story 文件数量。
- P5-E1 到 P5-E9 的 Epic 数量和每个 Epic 的 Story 数。
- 与第五阶段产品技术设计文档第 15 节实施优先级、18 节验收清单是否一致。
- 是否覆盖第五阶段原型新增页面：Prompt 治理、知识库、邮件回复审核、质量指标。

结论：

- 通过。README 共规划 48 个 Story，覆盖 9 个 Epic。
- 通过。Epic 分布为 6、6、5、5、5、5、6、5、5，覆盖数据底座、Prompt 治理、知识库、embedding、后台、规则审计、EMAIL_REPLY Agent、邮件发送和端到端验收。
- 通过。已覆盖产品文档第 14 节 Go/No-Go 指标和第 18 节验收清单中的核心能力。
- 通过。已覆盖 `prototypes/mvp-mobile-agent` 第五阶段新增后台和移动端邮件回复原型。

发现项：

- 初始拆分中容易把后台页面和 API 能力混在同一 Story，导致验收边界过大。

修正结果：

- 已将后台页面拆为 P5-E5，API/服务能力分别放入 P5-E2、P5-E3、P5-E6、P5-E8，保证每个 Story 可独立执行和验收。

### 第二轮独立复核：Story 质量、风险边界与可执行性检查

复核维度：

- 每个 Story 是否包含状态、Sprint、优先级、Epic、用户故事、上下文来源、目标、建议文件、验收标准、非目标和 Codex 提示词。
- 是否明确真实 PostgreSQL/API 联调要求，不允许 seed 静态页面替代。
- 是否明确 `apps/api` 是业务数据权威，`apps/agents` 不直接写 core 业务表。
- 是否明确 DNC/勿扰、D/E 级、语言不确定、知识不足、价格/付款/合同/法律/交付/出口管制等硬拦截。
- 是否把 AI 建议回复和最终发送内容分开审计。

结论：

- 通过。48 个 Story 均具备必要结构字段和可执行验收标准。
- 通过。所有 Story 均继承真实 API、PostgreSQL、Redis、两轮评审和中文记录要求。
- 通过。P5-E6、P5-E7、P5-E8 明确自动发送准入、硬拦截、Agent 边界和邮件发送前检查。
- 通过。P5-E1-S3、P5-E6-S4、P5-E8-S3 明确 AI 建议与最终发送内容分开保存和审计。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
