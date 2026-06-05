# Story P5-E9-S1：Prompt、知识与 embedding 指标服务

状态：已完成
Sprint：Sprint 9  
优先级：P1  
Epic：P5-E9（质量指标与端到端验收）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现 Prompt 入库覆盖率、知识发布数量、embedding ready 率和失败统计指标，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现 Prompt 入库覆盖率、知识发布数量、embedding ready 率和失败统计指标。

**建议文件：**

- apps/api/app/services/*metrics*
- apps/api/app/routers/*metrics*
- apps/api/tests/*metrics*

**验收标准：**

- Prompt 入库覆盖率可按 `prompts/` 文件统计。
- embedding ready 率可按已发布知识统计。
- 指标用于 admin-email-quality 页面。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E9-S1：Prompt、知识与 embedding 指标服务。
目标：实现 Prompt 入库覆盖率、知识发布数量、embedding ready 率和失败统计指标。
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

## 本次执行记录（2026-06-06）

### TDD 红灯

先新增 `apps/api/tests/test_phase5_prompt_knowledge_embedding_metrics_api.py`，覆盖统一质量基础指标 API：

- 从 `prompts/*.md` 解析 expected Prompt 文件清单。
- 基于 `llm_prompt_templates.source_file_path/source_file_hash/status/is_default` 统计 Prompt 入库覆盖率。
- 基于已发布知识统计 `published_knowledge_count`、`active_for_retrieval_count` 和 `auto_reply_allowed_count`。
- 基于已发布知识关联的 `knowledge_embeddings` 统计 ready、pending、failed、ready rate 和 retry。

同时更新 `apps/admin/tests/emailQualityDashboard.test.mjs`，要求 admin 邮件质量页请求 `/dashboard/phase5-quality-foundation` 并保留统一指标 payload。

红灯命令与结果：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_knowledge_embedding_metrics_api.py -q
```

- 结果：`1 failed`
- 失败原因：`/dashboard/phase5-quality-foundation` 返回 404，确认统一指标 API 尚未实现。

```bash
export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH
npm --prefix apps/admin test -- tests/emailQualityDashboard.test.mjs
```

- 结果：`1 failed`
- 失败原因：admin 邮件质量页尚未请求 `/dashboard/phase5-quality-foundation`。

### 最小实现

本次新增和更新：

- 在 `apps/api/app/services/dashboard.py` 新增 `phase5_quality_foundation_metrics()`，聚合 Prompt、知识和 embedding 基础质量指标。
- 在 `apps/api/app/schemas/dashboard.py` 新增 `Phase5QualityFoundationResponse` 及 Prompt、知识、embedding 子指标 schema。
- 在 `apps/api/app/api/dashboard.py` 新增 `GET /dashboard/phase5-quality-foundation`，支持 `knowledge_collection_prefix` 用于测试和排查时限定知识集合。
- 在 `apps/admin/src/services/emailQualityDashboard.js` 中接入 `/dashboard/phase5-quality-foundation`，让 `admin-email-quality` 页面能消费统一基础指标。

### 绿灯与回归验证

定向绿灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_knowledge_embedding_metrics_api.py -q
```

结果：

- `1 passed, 11 warnings`

后端相关回归命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  tests/test_phase5_prompt_knowledge_embedding_metrics_api.py \
  tests/test_phase5_prompt_file_parser.py \
  tests/test_phase5_prompt_import_service.py \
  tests/test_phase5_embedding_metrics_failed_cases.py \
  tests/test_phase5_embedding_async_worker.py \
  tests/test_phase5_knowledge_review_publish_archive_api.py \
  tests/test_phase5_knowledge_quality_usage_api.py \
  tests/test_phase5_email_failure_bounce_api.py -q
```

结果：

- `19 passed, 103 warnings`
- warnings 为既有 `datetime.utcnow()` deprecation，不影响本 Story 验收。

后台质量页验证命令：

```bash
export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH
npm --prefix apps/admin test -- tests/emailQualityDashboard.test.mjs
npm --prefix apps/admin run check:syntax
```

结果：

- admin 测试：`43 passed`
- admin 语法检查：通过

### 第一轮独立多维度评审

结论：通过。

发现项：

- TDD 顺序有效：先确认后端统一指标接口 404、前端未请求统一指标接口，再实现最小 API 与前端接入。
- Prompt 覆盖率来自真实 `prompts/*.md` 扫描和真实 `llm_prompt_templates` 表，不依赖 seed 静态数据。
- 知识发布与 embedding ready 率来自真实 `knowledge_items` 与 `knowledge_embeddings` 表，测试仅通过 marker 限定清理范围，未破坏真实业务数据。
- admin 邮件质量页已请求统一基础指标 API，同时保留既有 Prompt、embedding、审计、草稿和风险事件 API。

修正结果：

- 发现后端 ready rate 因四舍五入导致 `1/3` 精度不符合测试，已改为返回原始比例。

### 第二轮独立多维度评审

结论：通过。

发现项：

- 本 Story 只补齐 P5-E9-S1 的 Prompt、知识与 embedding 基础质量指标，没有进入 P5-E9-S2 的采纳率、编辑幅度、退信率完整口径。
- 实现继续遵守 `apps/api` 业务数据权威，`apps/admin` 只读取真实 API，不直接访问业务表。
- 新增 `knowledge_collection_prefix` 仅用于测试和排查过滤，不影响默认全局统计。
- 未发现绕过 DNC/D/E、硬拦截、自动发送准入或 AI 建议/最终发送分离审计的风险。

修正结果：

- 未发现新增实质阻塞问题，当前 Story 可标记为已完成。

### 残留风险

- P5-E9-S1 只提供质量基础指标；AI 回复生成成功率、人工采纳率、编辑幅度、自动发送成功率、退信率和客户回复率仍由 P5-E9-S2 补齐。
- `admin-email-quality` 当前仍同时请求统一基础指标和既有分散指标；后续 P5-E9-S2/P5-E9-S3 可进一步统一 Go/No-Go 聚合口径。
