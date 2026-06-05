# Story P5-E4-S2：发布后异步生成 pgvector embedding worker

状态：已完成
Sprint：Sprint 4  
优先级：P0  
Epic：P5-E4（pgvector embedding 异步）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现异步 worker，在知识发布后生成 pgvector embedding 并更新状态，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现异步 worker，在知识发布后生成 pgvector embedding 并更新状态。

**建议文件：**

- apps/api/app/workers/*embedding*
- apps/api/app/services/*embedding*
- apps/api/tests/*embedding_worker*

**验收标准：**

- 发布接口返回 pending_embedding，worker 后台生成向量。
- embedding_dimensions 和 embedding_model 入库。
- LLM/embedding 服务异常时不影响主 API。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E4-S2：发布后异步生成 pgvector embedding worker。
目标：实现异步 worker，在知识发布后生成 pgvector embedding 并更新状态。
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

- 新增 `apps/api/tests/test_phase5_embedding_async_worker.py`。
- 覆盖发布后异步 embedding worker 的核心行为：
  - 发布接口返回 `workflow_state=pending_embedding`。
  - 发布后创建 `pending` embedding 任务，记录 `embedding_model` 与 `embedding_dimensions`。
  - 后台 worker 生成 1536 维向量后将任务更新为 `ready`。
  - embedding provider 异常时发布 API 仍返回 200，任务由 worker 更新为 `failed` 并记录错误。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_async_worker.py -q`
- 红灯结果：2 个收集错误。
  - `app.api.knowledge` 尚未暴露 `create_embedding_provider`。
  - 当前发布接口没有 embedding provider 注入点，也没有后台 worker 启动入口。

### 实现摘要

- 新增 `apps/api/app/services/embedding_provider.py`：
  - 定义 `EmbeddingProvider` 协议。
  - 新增 `OpenAICompatibleEmbeddingProvider`，调用 OpenAI-compatible `/embeddings` 接口。
  - 支持独立 embedding 配置；未配置独立 key/base_url 时回退既有 LLM 配置。
- 新增 `apps/api/app/services/knowledge_embedding_worker.py`：
  - `KnowledgeEmbeddingWorker.run_once(embedding_id)` 独立打开数据库会话。
  - 从知识标题、正文、语言、国家和业务 metadata 构建 embedding 文本。
  - 成功时写入向量、`embedding_model`、`embedding_dimensions`，并把任务置为 `ready`。
  - 失败时清空向量、记录 `error_message`，并把任务置为 `failed`。
- 扩展 `KnowledgeService`：
  - `create_pending_embedding_task`
  - `mark_embedding_ready`
  - `mark_embedding_failed`
- 修改 `POST /knowledge/items/{item_id}/publish`：
  - 发布事务内创建 pending embedding 任务。
  - 提交后通过 `AgentThreadRunner.start` 启动 `knowledge-embedding-worker-{embedding_id}` 后台线程。
  - 后台 worker 失败不影响主发布 API。
- 扩展 `Settings`：
  - `LLM_EMBEDDING_MODEL` / `VEHICLE_LEADS_LLM_EMBEDDING_MODEL`
  - `LLM_EMBEDDING_DIMENSIONS` / `VEHICLE_LEADS_LLM_EMBEDDING_DIMENSIONS`
  - `LLM_EMBEDDING_BASE_URL` / `VEHICLE_LEADS_LLM_EMBEDDING_BASE_URL`
  - `LLM_EMBEDDING_API_KEY` / `VEHICLE_LEADS_LLM_EMBEDDING_API_KEY`
- 更新 `apps/api/tests/test_llm_settings.py`，覆盖新增 embedding 配置默认值与 env alias。

### 系统化调试记录

- 首轮实现后运行 Story 测试出现收集错误：
  - `ValueError: mutable default <class 'app.settings.Settings'> for field settings is not allowed`
- 根因：
  - `OpenAICompatibleEmbeddingProvider` 使用 `@dataclass`，直接把 `settings` 对象作为默认字段值。
- 修正：
  - 改为 `field(default_factory=lambda: settings)`。
- 复测：
  - `tests/test_phase5_embedding_async_worker.py` 转绿。

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_async_worker.py -q`
  - 结果：`2 passed, 16 warnings`。
- 配置契约与 Story 测试：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_llm_settings.py tests/test_phase5_embedding_async_worker.py -q`
  - 结果：`5 passed, 16 warnings`。
- 知识库与 embedding 回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_async_worker.py tests/test_phase5_embedding_task_status_retry_service.py tests/test_phase5_knowledge_retrieval_filter_api.py tests/test_phase5_knowledge_review_publish_archive_api.py tests/test_phase5_knowledge_crud_api.py tests/test_phase5_knowledge_business_fields.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py tests/test_phase_one_knowledge_import.py tests/test_phase5_knowledge_usage_quality_model.py -q`
  - 结果：`37 passed, 145 warnings`。
- 代码检查：
  - `git diff --check`
  - 结果：无输出，未发现空白或 patch 格式问题。
- 已知 warning：
  - 知识库服务仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，属于既有技术债，非本 Story 行为阻塞。

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、架构边界和状态流

- 结论：P5-E4-S2 的验收标准已覆盖；发布接口返回 `pending_embedding`，发布后创建 pending 任务，worker 可将任务更新为 `ready` 或 `failed`。
- 发现项 1：发布接口必须不等待外部 embedding 服务，否则第五阶段后台发布会被 provider 延迟或故障拖垮。
- 修正结果 1：发布事务只创建 pending 任务；外部 provider 调用只发生在 `AgentThreadRunner` 后台线程中。
- 发现项 2：embedding provider 异常必须可观测，不能吞掉后让任务长期 pending。
- 修正结果 2：worker 捕获异常后将任务置为 `failed`，保存 `error_message`，并通过日志记录失败。
- 发现项 3：`apps/api` 应继续作为业务数据权威，不能让 `apps/agents` 或前端直接写 embedding 任务。
- 修正结果 3：本 Story 所有业务写入均位于 `apps/api` 的 `KnowledgeService` 和 worker 内，未改动 `apps/agents`，未引入前端直写。
- 发现项 4：新增 provider 需要生产配置入口，否则只能测试 fake provider。
- 修正结果 4：补充 embedding model、dimensions、base_url、api_key 配置，并保留对既有 LLM 配置的回退。

### 第二轮评审：回归风险、可运维性和文档回写

- 结论：第二轮未发现新增实质阻塞问题；实现范围保持在 P5-E4-S2，没有执行 stale 处理、RAG 召回测试 API 或后续 Story。
- 发现项 1：发布测试中真实环境若没有 embedding key，后台线程可能失败，但不能影响发布 API 或既有知识审核测试。
- 修正结果 1：回归验证中 `test_phase5_knowledge_review_publish_archive_api.py` 仍通过；worker 失败只更新 embedding 任务状态，不改变知识发布响应。
- 发现项 2：新增测试文件在当前仓库规则下被 `.gitignore` 忽略，若提交时不强制 add 会丢失验证资产。
- 修正结果 2：提交前将使用 `git add -f apps/api/tests/test_phase5_embedding_async_worker.py`。
- 发现项 3：`embedding_dimensions` 与实际向量长度若不一致，会造成 pgvector 写入或检索质量风险。
- 修正结果 3：worker 在写入前校验 provider 声明维度与实际向量长度一致，不一致则置为 `failed`。
- 发现项 4：文档需要记录红灯、实现、验证和两轮评审，否则不满足 `docs/AI协同开发执行标准.md`。
- 修正结果 4：当前 Story 已补充完整执行记录、验证命令和两轮评审结论。
