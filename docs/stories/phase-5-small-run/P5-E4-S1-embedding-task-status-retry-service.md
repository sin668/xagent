# Story P5-E4-S1：embedding 任务状态与重试服务

状态：已完成
Sprint：Sprint 4  
优先级：P0  
Epic：P5-E4（pgvector embedding 异步）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现知识发布后的 embedding 任务状态管理、失败原因记录和重试入口，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现知识发布后的 embedding 任务状态管理、失败原因记录和重试入口。

**建议文件：**

- apps/api/app/services/*embedding*
- apps/api/app/routers/*knowledge*
- apps/api/tests/*embedding*

**验收标准：**

- pending、ready、failed 状态流转清晰。
- 失败可记录 error_message 并支持人工重试。
- 不会阻塞知识发布接口。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E4-S1：embedding 任务状态与重试服务。
目标：实现知识发布后的 embedding 任务状态管理、失败原因记录和重试入口。
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

- 新增 `apps/api/tests/test_phase5_embedding_task_status_retry_service.py`。
- 覆盖 embedding 任务状态流转和人工重试入口：
  - 无向量且无错误时创建 `pending` 任务。
  - 有错误时创建 `failed` 任务并保存 `error_message`。
  - `failed` 任务可通过人工 retry 回到 `pending`，并清空 `error_message`。
  - `ready` 任务不允许 retry，返回 409。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_task_status_retry_service.py -q`
- 红灯结果：2 个失败。
  - 无向量、无错误的 embedding 被误标记为 `ready`。
  - `/knowledge/embeddings/{embedding_id}/retry` 返回 404。

### 实现摘要

- 修正 `KnowledgeService.build_embedding_payload` 的状态映射：
  - `error_message` 存在：`failed`。
  - `embedding is None` 且无错误：`pending`。
  - `embedding` 存在：`ready`。
- 新增 `KnowledgeService.retry_embedding`：
  - 只允许 `failed -> pending`。
  - 清空 `embedding` 和 `error_message`。
  - 非 `failed` 状态抛出权限错误。
- 新增 API：
  - `POST /knowledge/embeddings/{embedding_id}/retry`
- 错误语义：
  - embedding 任务不存在：404。
  - 非 failed 状态重试：409，提示 `只有 failed 状态的 embedding 任务可以重试。`
- 发布接口仍只进入 `pending_embedding` 元数据状态，不等待 embedding 生成，本 Story 未引入阻塞式生成流程。

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_task_status_retry_service.py -q`
  - 结果：`2 passed, 11 warnings`。
- 已知 warning：
  - 知识库服务仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，非本 Story 行为阻塞。

## 两轮独立多维度评审

### 第一轮评审：状态流、错误记录和重试入口

- 结论：P5-E4-S1 已建立 embedding 任务的 `pending -> ready/failed -> retry pending` 状态管理能力。
- 发现项 1：原有状态映射把无向量、无错误的任务标记为 `ready`，会让未生成 embedding 的知识误入 ready 语义。
- 修正结果 1：`build_embedding_payload` 改为按 `error_message`、`embedding is None`、`embedding exists` 三类映射到 `failed/pending/ready`。
- 发现项 2：失败任务只有错误记录，没有人工 retry API，后台无法恢复失败任务。
- 修正结果 2：新增 `/knowledge/embeddings/{embedding_id}/retry`，将 failed 任务重置为 pending。
- 发现项 3：ready 任务如果允许 retry，会破坏已可召回知识的稳定状态。
- 修正结果 3：非 failed 状态 retry 返回 409。

### 第二轮评审：发布非阻塞、范围控制和兼容性

- 结论：第二轮未发现新增实质阻塞问题；当前实现只覆盖 P5-E4-S1，没有执行异步 embedding worker、stale 处理或 RAG 召回测试 API。
- 发现项 1：P5-E4-S1 的验收要求知识发布接口不阻塞。
- 修正结果 1：本 Story 未改动发布接口的同步行为；发布仍只写 `workflow_state=pending_embedding`，embedding 任务由后续 Story/入口处理。
- 发现项 2：更改 embedding 状态映射可能影响现有失败 payload 测试。
- 修正结果 2：保留 `error_message -> failed` 和 `embedding exists -> ready`，只修正无向量无错误为 `pending`。
- 发现项 3：retry 清空错误时不应删除任务记录，避免审计链路断裂。
- 修正结果 3：retry 在原 `KnowledgeEmbedding` 记录上更新状态和错误字段，不新建或删除记录。
