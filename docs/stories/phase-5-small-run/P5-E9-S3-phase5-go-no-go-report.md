# Story P5-E9-S3：第五阶段 Go/No-Go 报告 API 与文档

状态：已完成
Sprint：Sprint 9  
优先级：P1  
Epic：P5-E9（质量指标与端到端验收）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望生成第五阶段 Go/No-Go 报告，覆盖 Prompt、embedding、Agent、采纳率、硬拦截和风险事件，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 生成第五阶段 Go/No-Go 报告，覆盖 Prompt、embedding、Agent、采纳率、硬拦截和风险事件。

**建议文件：**

- apps/api/app/services/*report*
- docs/poc/*
- docs/product/*

**验收标准：**

- Go 条件与产品文档第 14 节一致。
- 支持重跑小范围和暂停自动发送结论。
- 报告包含数据来源和统计时间窗。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E9-S3：第五阶段 Go/No-Go 报告 API 与文档。
目标：生成第五阶段 Go/No-Go 报告，覆盖 Prompt、embedding、Agent、采纳率、硬拦截和风险事件。
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
执行方式：按 `superpowers:test-driven-development`、`superpowers:systematic-debugging` 和 `superpowers:verification-before-completion` 推进。

### TDD 红灯

- 新增 `apps/api/tests/test_phase5_go_no_go_report_api.py`，使用真实 PostgreSQL 构造三组时间窗：
  - `go`：Prompt 覆盖、embedding ready、AI 生成、人工采纳、硬拦截和风险事件均满足产品第 14 节。
  - `rerun_small_scope`：无硬风险事件，但人工采纳率低、编辑幅度高、发送失败率偏高。
  - `pause_auto_send`：存在投诉/建议暂停风险事件。
- 红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_go_no_go_report_api.py -q
```

- 红灯结果：`3 failed`，失败原因是 `/dashboard/phase5-go-no-go-report` 返回 `404 Not Found`，证明报告 API 尚未实现。

### 实现内容

- 新增 `GET /dashboard/phase5-go-no-go-report`。
- 新增 `Phase5GoNoGoReportResponse`、`Phase5GoNoGoMetrics`、`Phase5GoNoGoCriterion` 等响应 schema。
- 在 `DashboardService.phase5_go_no_go_report()` 中汇总：
  - Prompt 入库覆盖率。
  - 已发布知识 embedding ready 率。
  - AI 回复建议生成成功率。
  - 人工采纳率和平均编辑幅度。
  - 自动发送成功率和发送失败率。
  - 硬拦截准确执行率。
  - DNC/勿扰、D/E、语言不确定、缺少同语言知识、缺少知识证据、知识召回不足等自动发送拦截率。
  - 投诉、封禁、违规或建议暂停风险事件数量。
- 支持 `date_from`、`date_to`、`language`、`business_scene` 和 `knowledge_collection_prefix` 过滤。
- 新增中文报告口径文档：`docs/product/2026-06-06-海外车辆采购AI获客系统-第五阶段Go-No-Go报告口径.md`。

### 调试归因

- 首轮实现后测试出现 `TypeError: can't compare offset-naive and offset-aware datetimes`。
  - 根因：API 日期参数解析为 naive datetime，而测试和真实库中部分 `created_at` 为 UTC aware datetime。
  - 修正：`within_date_range()` 按被比较值的时区对齐日期边界。
- 第二轮实现后 `rerun_small_scope` 被误判为 `go`。
  - 根因：报告层将硬拦截草稿纳入人工采纳率分母，硬拦截草稿正文未改导致人工采纳率被稀释为高值。
  - 修正：Go/No-Go 报告中的回复质量指标只统计可回复草稿；硬拦截草稿单独进入硬风险指标。

### 验证结果

目标测试：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_go_no_go_report_api.py -q
```

结果：`3 passed`。

相关后端回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_go_no_go_report_api.py tests/test_phase5_email_reply_quality_metrics_api.py tests/test_phase5_prompt_knowledge_embedding_metrics_api.py tests/test_phase5_email_failure_bounce_api.py tests/test_phase5_email_manual_send_api.py tests/test_phase5_email_auto_send_api.py tests/test_phase5_email_reply_audit_service.py -q
```

结果：`14 passed`。

## 两轮独立多维度评审

### 第一轮评审

结论：通过。

发现项：

- 需求覆盖：报告 API 覆盖 Prompt、embedding、AI 生成、人工采纳、编辑幅度、硬拦截、风险事件和邮件发送结果。
- 产品一致性：Go 条件与产品文档第 14 节保持一致，支持 `go`、`rerun_small_scope` 和 `pause_auto_send` 三种结论。
- 数据来源：响应明确回显 `llm_prompt_templates`、`knowledge_items`、`knowledge_embeddings`、`email_reply_drafts`、`email_send_attempts` 和 `risk_events`。
- 时间窗：响应明确回显 `date_from/date_to`，测试用未来日期窗口隔离现有数据。
- 架构边界：报告由 `apps/api` 生成，未让 Agent 或前端自行判断放量。

修正结果：

- 已修正日期边界的时区兼容问题。
- 已补充独立 Go/No-Go 报告口径文档。

### 第二轮评审

结论：通过。

发现项：

- 回归风险：P5-E9-S1/P5-E9-S2 相邻指标回归通过，新增报告未改动 EMAIL_REPLY Agent、发送接口或自动发送准入逻辑。
- 口径清晰：硬拦截草稿不进入人工采纳率分母，避免将正确阻断误判为回复质量采纳。
- 风控边界：DNC/D/E、知识/语言硬拦截、投诉/违规风险事件均可触发暂停自动发送。
- 文档回写：Story 已记录 TDD、调试归因、验证命令、两轮评审和残留风险。
- 未发现新增实质阻塞问题。

修正结果：

- 无需继续修正。

## 残留风险

- 当前报告 API 复用已有指标服务并在内存中完成部分聚合，适合第五阶段小范围运行；生产化后应将大数据量统计改为 SQL 聚合或物化指标。
- 当前 `pause_auto_send` 风险事件类型基于 `risk_events.event_type` 和 `pause_suggested` 识别；后续如新增风险类型，需要同步扩展报告口径文档和测试。
