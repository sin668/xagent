# Story P5-E4-S5：embedding 指标与失败案例

状态：已完成
Sprint：Sprint 4  
优先级：P1  
Epic：P5-E4（pgvector embedding 异步）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望统计 embedding ready 率、失败原因、重试次数和失败案例，供质量看板使用，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 统计 embedding ready 率、失败原因、重试次数和失败案例，供质量看板使用。

**建议文件：**

- apps/api/app/services/*metrics*
- apps/api/app/routers/*metrics*
- apps/api/tests/*embedding_metrics*

**验收标准：**

- 可计算已发布知识 embedding ready 率。
- 失败原因可分组统计。
- 指标支持 Go/No-Go 使用。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E4-S5：embedding 指标与失败案例。
目标：统计 embedding ready 率、失败原因、重试次数和失败案例，供质量看板使用。
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

### TDD 红灯

- 新增 `apps/api/tests/test_phase5_embedding_metrics_failed_cases.py`。
- 覆盖 embedding 质量看板基础口径：
  - 已发布知识数量。
  - embedding 任务总数。
  - ready/pending/failed 数量。
  - ready 率。
  - retry 总次数。
  - 失败原因分组。
  - 失败案例列表。
  - Go/No-Go ready 判断。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_metrics_failed_cases.py -q`
- 红灯结果：1 个失败。
  - retry 响应缺少 `retry_count`，说明当前表结构和 API 不能统计重试次数。

### 实现摘要

- 新增 Alembic migration：
  - `apps/api/alembic/versions/20260605_0035_add_knowledge_embedding_retry_metrics.py`
  - 为 `knowledge_embeddings` 增加：
    - `last_error_message`
    - `retry_count`
    - `ix_knowledge_embeddings_retry_count`
- 更新真实 PostgreSQL：
  - 执行 `/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head`
  - 数据库 revision 已升级到 `20260605_0035`。
- 更新模型与 schema：
  - `KnowledgeEmbedding.last_error_message`
  - `KnowledgeEmbedding.retry_count`
  - `KnowledgeEmbeddingResponse.last_error_message`
  - `KnowledgeEmbeddingResponse.retry_count`
  - `KnowledgeEmbeddingMetricsResponse`
- 更新 `KnowledgeService`：
  - 创建 failed embedding 时同步写入 `last_error_message`。
  - worker 标记 failed 时同步写入 `last_error_message`。
  - retry failed embedding 时将 `retry_count + 1`，并保留最后失败原因。
- 新增 `KnowledgeEmbeddingMetricsService`：
  - 以 `active + approved` 知识作为已发布知识口径。
  - 统计 ready/pending/failed、ready_rate、total_retry_count。
  - 按 `last_error_message/error_message` 分组失败原因。
  - 输出失败案例，用于后台质量看板和 Go/No-Go。
- 新增 API：
  - `GET /knowledge/embeddings/metrics`

### 系统化调试记录

- 第一轮实现后运行 Story 测试失败：
  - `ready_rate` 返回 `0.3333`，测试期望 `1/3`。
- 根因：
  - 指标服务对 ready_rate 做了四位小数截断，会影响 Go/No-Go 边界判断。
- 修正：
  - ready_rate 保留原始比例，由前端展示层决定格式化。
- 第二轮验证失败：
  - retry 后 `failure_reason_groups` 为空。
- 根因：
  - retry 会清空 `error_message`，但未在清空前沉淀 `last_error_message`。
- 修正：
  - retry 时执行 `last_error_message = last_error_message or error_message`，保留最近失败原因。
- 第三轮验证失败：
  - migration contract 测试仍只期望到 `20260605_0034`。
- 修正：
  - 更新 `PHASE5_MIGRATION_CONTRACTS` 和 `test_phase5_migration_contracts.py`，纳入 `20260605_0035`。

### 真实 PostgreSQL / API 验证

- migration 与当前 Story 验证：
  - `/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head`
  - 结果：成功执行 `20260605_0034 -> 20260605_0035`。
- 当前 Story、migration contract、schema 和 retry 回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_metrics_failed_cases.py tests/test_phase5_migration_contracts.py tests/test_knowledge_schema.py tests/test_phase5_embedding_task_status_retry_service.py -q`
  - 结果：`12 passed, 22 warnings`。
- 已知 warning：
  - 知识库服务仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，属于既有技术债，非本 Story 行为阻塞。

## 两轮独立多维度评审

### 第一轮评审：指标口径、失败案例和重试追踪

- 结论：P5-E4-S5 的验收标准已覆盖；系统可计算已发布知识 embedding ready 率，按失败原因分组，并输出失败案例和 retry 次数。
- 发现项 1：仅依赖当前 `error_message` 无法统计 retry 后的失败案例，因为 retry 会清空错误并回到 pending。
- 修正结果 1：新增 `last_error_message`，retry 后仍能保留最近失败原因用于质量看板。
- 发现项 2：Story 要求重试次数，但原表没有字段。
- 修正结果 2：新增 `retry_count` 字段，并在 retry API 中递增。
- 发现项 3：ready_rate 若被后端四舍五入，Go/No-Go 临界值可能误判。
- 修正结果 3：后端返回原始比例，展示格式交给前端。

### 第二轮评审：迁移安全、API 边界和范围控制

- 结论：第二轮未发现新增实质阻塞问题；实现范围保持在 P5-E4-S5，没有执行后台质量页面或后续 EMAIL_REPLY Story。
- 发现项 1：真实 PostgreSQL schema 必须与模型一致，否则线上 metrics API 会访问不存在字段。
- 修正结果 1：新增并执行 Alembic `20260605_0035`，同步更新 migration contract。
- 发现项 2：metrics API 不应写入业务数据或触发 embedding worker。
- 修正结果 2：`GET /knowledge/embeddings/metrics` 只读 `knowledge_items/knowledge_embeddings`。
- 发现项 3：失败案例列表需要支持 retry 后仍可见，但不能把 retry pending 误算作 failed_count。
- 修正结果 3：`failed_count` 使用当前状态；`failed_cases` 使用历史 `last_error_message`。
- 发现项 4：新增测试文件受 `.gitignore` 影响，普通 `git status` 不显示。
- 修正结果 4：提交前将使用 `git add -f apps/api/tests/test_phase5_embedding_metrics_failed_cases.py`。
