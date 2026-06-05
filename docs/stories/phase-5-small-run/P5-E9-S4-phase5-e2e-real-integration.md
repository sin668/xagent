# Story P5-E9-S4：第五阶段端到端真实联调验收

状态：已完成
Sprint：Sprint 9
优先级：P0
Epic：P5-E9（质量指标与端到端验收）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望完成 Prompt 入库、知识发布、embedding、邮件导入、EMAIL_REPLY、人工确认/自动发送、触达历史和指标的端到端联调，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-05-第五阶段小范围运行-Prompt与邮件自动回复知识库.md`
- `docs/product/2026-06-05-海外车辆采购AI获客系统-第五阶段小范围运行方案与产品技术设计.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `prototypes/mvp-mobile-agent/pages/email-replies.html`
- `prototypes/mvp-mobile-agent/pages/email-reply-detail.html`
- `prototypes/mvp-mobile-agent/pages/admin-prompt-governance.html`
- `prototypes/mvp-mobile-agent/pages/admin-knowledge-base.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-replies.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-quality.html`

## Story 定义

**目标：** 完成 Prompt 入库、知识发布、embedding、邮件导入、EMAIL_REPLY、人工确认/自动发送、触达历史和指标的端到端联调。

**建议文件：**

- apps/api/tests/e2e/*
- apps/agents/tests/e2e/*
- apps/admin/tests/*
- docs/*

**验收标准：**

- 联调使用真实 PostgreSQL、Redis、apps/api、apps/agents 和 apps/admin API。
- 覆盖人工确认发送和自动发送候选被阻断场景。
- 不得仅使用 seed 静态页面作为验收。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E9-S4：第五阶段端到端真实联调验收。
目标：完成 Prompt 入库、知识发布、embedding、邮件导入、EMAIL_REPLY、人工确认/自动发送、触达历史和指标的端到端联调。
要求：使用 TDD；只实现本 Story；接入真实 PostgreSQL/API；完成后执行两轮独立多维度评审并用中文记录结论、发现项和修正结果。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 代码实现必须使用 `superpowers:test-driven-development`；调试异常必须使用 `superpowers:systematic-debugging`；完成前必须使用 `superpowers:verification-before-completion`。
- 环境按项目约定使用 `conda activate booking-room` 和 `nvm use v22.22.0`。
- 后端、Agent、后台和移动端联调必须使用真实 API、真实 PostgreSQL 和 Redis，不允许只验证 seed 静态页面。
- 每个 Story 完成后必须执行两轮独立多维度评审，并在 Story 或执行记录中写明结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 是唯一业务数据权威，业务 core 表写入、权限、审计、DNC/勿扰、自动发送准入、硬拦截和邮件发送提交必须由 `apps/api` 控制。
- `apps/agents` 只做编排、LLM 调用、节点追踪和结果回传，不直接写 `customers`、`contact_methods`、`lead_sources`、`knowledge_items`、`email_reply_drafts`、`outreach_records` 等业务 core 表。
- 不自动社交私信、不自动加好友、不登录后批量采集、不反爬规避、不抓取非公开数据。
- DNC/勿扰、Watch/Invalid（对外 D/E 级）、语言不确定、知识召回不足、缺少知识证据、价格/付款/合同/发票/税务/法律/交付/出口管制等场景不得自动发送。
- LLM 输出必须结构化；缺失字段输出 `Unknown`、`null` 或空数组，不得编造。
- AI 建议回复和最终发送内容必须分开保存并可审计。

## 执行记录

执行日期：2026-06-06
执行人：Codex
执行方式：Superpowers TDD + 系统化调试 + 完成前验证
真实环境：`apps/api/.env` PostgreSQL，Alembic head，admin 服务测试使用 Node v22.22.0

### TDD 红灯

新增测试：

- `apps/api/tests/test_phase5_e2e_integration_report_api.py`

红灯过程：

1. 首次运行目标测试时，真实 PostgreSQL 写入 `AgentTaskRun(task_type=EMAIL_REPLY)` 失败。
2. 系统化调试确认根因：代码和 Alembic 已有 `AgentTaskType.EMAIL_REPLY` / `20260605_0036_add_email_reply_agent_task_type.py`，但真实库 Alembic current 停在 `20260605_0035`，`agenttasktype` enum 尚无 `EMAIL_REPLY`。
3. 执行 `python -m alembic upgrade head` 后确认真实库 enum 已包含 `EMAIL_REPLY`。
4. 再次运行目标测试，红灯回到预期缺失能力：`GET /dashboard/phase5-e2e-integration-report` 返回 `404 Not Found`。

### 实现内容

- 新增 `GET /dashboard/phase5-e2e-integration-report`。
- 新增 `Phase5E2EIntegrationReportResponse`、阶段结果、summary 和 time window schema。
- 新增 `DashboardService.phase5_e2e_integration_report()`，按真实 PostgreSQL 证据检查 11 个阶段：
  - Prompt 入库
  - 知识发布
  - embedding ready
  - 邮件导入
  - EMAIL_REPLY Agent
  - 人工确认发送
  - 自动发送拦截
  - 触达历史
  - 质量指标
  - Go/No-Go 报告
  - 后台真实 API 契约
- 明确 `seed_fallback_allowed=false`，报告 notes 写明不得使用 seed 静态数据作为第五阶段验收依据。
- `apps/admin/src/services/adminRealApiIntegration.js` 补充三类真实 API 联调契约：
  - `/dashboard/email-reply-quality`
  - `/dashboard/phase5-go-no-go-report`
  - `/dashboard/phase5-e2e-integration-report`

### 测试命令与结果

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
```

结果：真实 PostgreSQL 起初为 `20260605_0035`，执行 migration 后到 `20260605_0036 (head)`。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_e2e_integration_report_api.py -q
```

结果：`1 passed`。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_e2e_integration_report_api.py tests/test_phase5_go_no_go_report_api.py tests/test_phase5_email_reply_quality_metrics_api.py -q
```

结果：`5 passed`。

```bash
export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH
npm --prefix apps/admin test -- tests/adminRealApiIntegration.test.mjs
```

结果：`43 passed`。

### 第一轮独立多维度评审

结论：通过。

发现项：

- 需求覆盖：已覆盖 Prompt 入库、知识发布、embedding、邮件导入、EMAIL_REPLY、人工确认发送、自动发送阻断、触达历史、质量指标、Go/No-Go 和后台真实 API 契约。
- 架构边界：新增报告只读聚合真实 PostgreSQL 证据，没有让 `apps/agents` 或前端写业务 core 表。
- 数据边界：`EMAIL_REPLY Agent` 阶段显式检查 `writes_core_tables=false`，符合 Agent 不直接写业务表边界。
- 真实联调：红灯过程暴露并修复真实库 migration 未到 head 的问题，未绕过 `EMAIL_REPLY` enum。
- 测试覆盖：后端目标测试和相关质量/Go-No-Go 回归通过，admin 真实 API 契约测试通过。

修正结果：

- 已执行真实 PostgreSQL migration 到 `20260605_0036`。
- 已补充后端 E2E 报告 API 和 admin 真实 API 契约检查。

### 第二轮独立多维度评审

结论：通过。

发现项：

- 回归风险：新增接口为只读 dashboard 聚合，不改变邮件发送、自动发送准入、硬拦截、EMAIL_REPLY Agent 或知识发布流程。
- 可观测性：报告按阶段返回 `status`、`evidence`、`findings`，可直接用于第五阶段验收和故障定位。
- 人工审核：报告只验证人工确认发送和硬拦截结果，不放宽自动发送准入规则。
- 文档回写：已记录红灯、真实库 enum/migration 根因、实现、测试命令、评审结论和残留风险。
- 未发现新增实质阻塞问题。

修正结果：

- 无需继续修正。

### 残留风险

- 当前 E2E 报告通过构造真实 PostgreSQL 证据链验证业务闭环，未启动真实 SMTP 服务商发送邮件；真实通道端到端发送仍应在 P5-E9-S5 归档前结合当前环境配置单独确认。
- `apps/api/app/services/knowledge.py` 仍存在 `datetime.utcnow()` 的弃用 warning，本 Story 未扩大修复范围。
