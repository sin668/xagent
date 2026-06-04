# Story P2-E5-S4：抽取结果写入 staging/core/audit 并更新来源抽取状态

状态：Done  
Sprint：Sprint 4  
优先级：P1  
Epic：P2-E5

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“抽取结果写入 staging/core/audit 并更新来源抽取状态”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 串联公开页面读取、LLM 抽取、分级、staging/core/audit 和来源状态更新。

**Files:**

- Modify: `apps/api/app/services/llm_lead_extraction.py`
- Modify: `apps/api/app/services/llm_lead_grading.py`
- Modify: `apps/api/app/services/lead_extraction_from_sources.py`
- Test: `apps/api/tests/test_lead_extraction_from_sources.py`

**Codex 提示词：**

```text
请执行 P2-E5-S4：抽取结果写入 staging/core/audit 并更新来源抽取状态。

要求：
1. 使用 superpowers:test-driven-development。
2. 页面读取只允许公开文本，不登录、不绕过验证码、不反爬规避。
3. 调用 LLMClient 执行抽取和分级。
4. 输出必须保留来源证据、prompt version、model、agent_task_run_id。
5. Invalid 和 Watch 不进入触达队列。
6. C 级必须标记合规复核。
7. 抽取成功后更新 lead_source_candidates.extraction_status 和 last_extracted_at。
8. 运行 pytest apps/api/tests/test_lead_extraction_from_sources.py apps/api/tests/test_llm_lead_extraction.py apps/api/tests/test_llm_lead_grading.py。
9. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e5-s4-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 抽取结果进入现有 staging/core 链路。
- 审计完整。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动抽取。
- Forbidden 来源不得进入自动抽取。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。

## 实施结果

已完成。

### 交付内容

- 新增：`apps/api/tests/test_lead_extraction_from_sources.py`
- 修改：`apps/api/app/services/lead_extraction_from_sources.py`
- 修改：`apps/api/app/services/llm_lead_extraction.py`
- 修改：`apps/api/app/services/llm_lead_grading.py`

### 实现说明

- 在 `LeadExtractionFromSourcesService` 中新增 `run_queued_lead_extraction_task()`，执行 `P2-E5-S3` 创建的 `LEAD_EXTRACTION` queued 来源任务。
- 将 `lead_source_candidates` 桥接到现有 raw/staging/core 链路：
  - 创建 `collection_tasks`
  - upsert `candidate_urls`
  - 创建 `page_snapshots`
  - 复用 `LLMLeadExtractionService.run_extraction()`
  - 复用 `LLMLeadGradingService.run_grading()`
- 页面读取边界：
  - 只使用来源候选的公开证据文本、发现理由和公开链接摘要。
  - 检测到登录墙、验证码或访问限制时停止抽取。
  - 不登录、不绕过验证码、不规避反爬、不保存非公开内容。
- LLM 调用：
  - 通过注入式 `LLMClient` 调用 `LEAD_EXTRACTION` 和 `LEAD_GRADING`。
  - 测试使用 fake LLMClient，不触发真实网络。
- 写回逻辑：
  - 抽取和分级成功后，来源候选 `extraction_status=succeeded`，写入 `last_extracted_at`。
  - LLM 技术失败时，来源候选 `extraction_status=retry`，任务按重试策略进入 `retry_pending`。
  - 任务成功时 `agent_task_runs.status=succeeded`，记录 processed/succeeded/failed 摘要。
- 审计增强：
  - `LLMLeadExtractionService.build_extraction_audit_input()` 支持 `agent_task_run_id`。
  - `LLMLeadGradingService.build_grading_audit_input()` 支持 `agent_task_run_id`。
  - 抽取和分级审计均保留来源 URL、prompt version、model 和 agent_task_run_id。
- 分级硬规则继续生效：
  - Invalid/Watch 不进入触达队列。
  - C 级自动标记 `requires_compliance_review=true`。

### TDD 记录

#### RED

先创建 `apps/api/tests/test_lead_extraction_from_sources.py`，覆盖：

- queued 来源执行后写入 staging、grading、audit。
- 来源候选成功后更新 `extraction_status=succeeded` 和 `last_extracted_at`。
- C 级分级结果标记合规复核。
- 审计记录包含来源、模型、prompt version 和 `agent_task_run_id`。
- LLM 技术失败时来源进入 `retry`，任务进入 `retry_pending`，不创建 staging。

运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_from_sources.py
```

结果：2 项失败，符合 RED 预期。

```text
TypeError: LeadExtractionFromSourcesService.__init__() got an unexpected keyword argument 'llm_client'
```

失败原因：服务尚未支持 LLMClient 注入，也没有 queued 来源执行方法。

#### GREEN

新增 LLMClient 注入、queued 执行方法、raw/staging 桥接和审计字段后，目标测试通过。

### 验证结果

Story 指定测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_from_sources.py apps/api/tests/test_llm_lead_extraction.py apps/api/tests/test_llm_lead_grading.py
```

结果：`13 passed`。

相关后端回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_from_sources.py apps/api/tests/test_lead_extraction_source_selection.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_agent_retries.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_sync_ai_audit_admin_api.py apps/api/tests/test_failed_cases_library.py
```

结果：`37 passed`。

语法检查：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/lead_extraction_from_sources.py apps/api/app/services/llm_lead_extraction.py apps/api/app/services/llm_lead_grading.py
```

结果：通过。

### 验收对照

- 页面读取只允许公开文本，不登录、不绕过验证码、不反爬规避：通过。
- 调用 LLMClient 执行抽取和分级：通过。
- 输出保留来源证据、prompt version、model、agent_task_run_id：通过。
- Invalid 和 Watch 不进入触达队列：通过，沿用 `LLMLeadGradingService.apply_hard_rules()`。
- C 级必须标记合规复核：通过。
- 抽取成功后更新 `lead_source_candidates.extraction_status` 和 `last_extracted_at`：通过。
- 抽取结果进入现有 staging/core 链路：通过，写入 staging，并保留可晋级 core 的既有链路。
- 审计完整：通过，抽取和分级均写入 AI audit。

### 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：queued 来源执行、公开文本摘要、LLM 抽取、LLM 分级、staging 写入、审计写入、来源状态回写均已实现。
- 合规边界：实现中不登录、不绕过验证码、不规避反爬；检测访问墙时停止抽取。
- 审计完整性：抽取和分级 audit 均包含来源、模型、prompt version 和 `agent_task_run_id`。
- 状态一致性：成功来源进入 `succeeded`，失败来源进入 `retry`，任务通过重试策略进入 `retry_pending`。
- 复用性：复用现有 `RawCollectionService`、`LLMLeadExtractionService`、`LLMLeadGradingService` 和 `StagingLeadService`，避免并行 staging 写入逻辑。
- 发现项：无新增实质问题。
- 修正结果：无需修正。

### 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：Story 指定测试 `13 passed`，相邻回归 `37 passed`。
- 产品边界：本 Story 实现来源候选到 staging/audit 的执行闭环；未做自动社交触达、加好友、登录后采集或反爬规避。
- 技术边界：为了兼容现有同步 SQLAlchemy 服务和异步 LLMClient，服务内提供隔离线程调用路径；测试使用 fake LLM，真实 LLM 可由后续调度/环境验证覆盖。
- 合规边界：Invalid/Watch 和 C 级规则沿用现有分级硬规则，C 级自动合规复核。
- 范围控制：未执行下一 Story；未做锁操作；未做 git 操作。
- 修正结果：无需修正。
