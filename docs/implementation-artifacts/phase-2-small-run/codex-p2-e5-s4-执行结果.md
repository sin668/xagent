# P2-E5-S4 抽取结果写入 staging/core/audit 并更新来源抽取状态执行结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E5-S4-lead-extraction-source-result-writeback.md`
- 状态：已完成
- 执行日期：2026-06-02
- 执行原则：每次只执行一个 Story；不做锁操作；不做 git 操作；使用 TDD；完成前执行验证；完成后执行两轮独立多维度评审。

## 交付内容

- 新增：`apps/api/tests/test_lead_extraction_from_sources.py`
- 修改：`apps/api/app/services/lead_extraction_from_sources.py`
- 修改：`apps/api/app/services/llm_lead_extraction.py`
- 修改：`apps/api/app/services/llm_lead_grading.py`
- 修改：`docs/stories/phase-2-small-run/P2-E5-S4-lead-extraction-source-result-writeback.md`

## 功能说明

### queued 来源执行

`LeadExtractionFromSourcesService` 新增 `run_queued_lead_extraction_task()`：

- 读取 `LEAD_EXTRACTION agent_task_runs.input_json.candidate_ids`。
- 只执行已进入 `queued` 的 `lead_source_candidates`。
- 将来源候选桥接到现有 raw/staging/core 链路：
  - 创建 `collection_tasks`
  - upsert `candidate_urls`
  - 创建 `page_snapshots`
  - 调用 `LLMLeadExtractionService.run_extraction()`
  - 调用 `LLMLeadGradingService.run_grading()`

### 公开文本边界

本 Story 的页面读取输入只来自来源候选中的公开证据字段：

- `evidence_note`
- `discovery_reason`
- `evidence_links`

实现边界：

- 不登录。
- 不绕过验证码。
- 不规避反爬。
- 不保存非公开内容。
- 检测到登录墙、验证码或访问限制时停止抽取。

### LLM 抽取和分级

- 通过注入式 `LLMClient` 调用 `LEAD_EXTRACTION` 和 `LEAD_GRADING`。
- 抽取结果写入 staging。
- 分级结果更新 staging 的推荐等级、队列状态和合规复核标记。
- Invalid/Watch 不进入触达队列。
- C 级自动标记 `requires_compliance_review=true`。

### 来源状态回写

- 抽取和分级成功：
  - `lead_source_candidates.extraction_status=succeeded`
  - `last_extracted_at` 写入执行时间
  - `agent_task_runs.status=succeeded`
- LLM 技术失败：
  - `lead_source_candidates.extraction_status=retry`
  - `last_extracted_at` 保持为空
  - `agent_task_runs` 通过重试策略进入 `retry_pending`

### 审计增强

- `LLMLeadExtractionService.build_extraction_audit_input()` 支持 `agent_task_run_id`。
- `LLMLeadGradingService.build_grading_audit_input()` 支持 `agent_task_run_id`。
- 抽取和分级审计均保留：
  - 来源 URL
  - prompt version
  - model
  - agent_task_run_id
  - LLM 输出
  - 风险阻断信息

## TDD 记录

### RED

先创建 `apps/api/tests/test_lead_extraction_from_sources.py`，覆盖以下行为：

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

### GREEN

新增 LLMClient 注入、queued 执行方法、raw/staging 桥接和审计字段后，目标测试通过：

```text
2 passed
```

## 验证结果

### Story 指定测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_from_sources.py apps/api/tests/test_llm_lead_extraction.py apps/api/tests/test_llm_lead_grading.py
```

结果：`13 passed`。

### 相关后端回归

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_from_sources.py apps/api/tests/test_lead_extraction_source_selection.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_agent_retries.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_sync_ai_audit_admin_api.py apps/api/tests/test_failed_cases_library.py
```

结果：`37 passed`。

### 语法检查

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/lead_extraction_from_sources.py apps/api/app/services/llm_lead_extraction.py apps/api/app/services/llm_lead_grading.py
```

结果：通过。

## 验收对照

- 页面读取只允许公开文本，不登录、不绕过验证码、不反爬规避：通过。
- 调用 LLMClient 执行抽取和分级：通过。
- 输出保留来源证据、prompt version、model、agent_task_run_id：通过。
- Invalid 和 Watch 不进入触达队列：通过。
- C 级必须标记合规复核：通过。
- 抽取成功后更新 `lead_source_candidates.extraction_status` 和 `last_extracted_at`：通过。
- 抽取结果进入现有 staging/core 链路：通过，写入 staging，并保留既有 core 晋级链路。
- 审计完整：通过，抽取和分级均写入 AI audit。

## 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：queued 来源执行、公开文本摘要、LLM 抽取、LLM 分级、staging 写入、审计写入、来源状态回写均已实现。
- 合规边界：实现中不登录、不绕过验证码、不规避反爬；检测访问墙时停止抽取。
- 审计完整性：抽取和分级 audit 均包含来源、模型、prompt version 和 `agent_task_run_id`。
- 状态一致性：成功来源进入 `succeeded`，失败来源进入 `retry`，任务通过重试策略进入 `retry_pending`。
- 复用性：复用现有 `RawCollectionService`、`LLMLeadExtractionService`、`LLMLeadGradingService` 和 `StagingLeadService`，避免并行 staging 写入逻辑。
- 发现项：无新增实质问题。
- 修正结果：无需修正。

## 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：Story 指定测试 `13 passed`，相邻回归 `37 passed`。
- 产品边界：本 Story 实现来源候选到 staging/audit 的执行闭环；未做自动社交触达、加好友、登录后采集或反爬规避。
- 技术边界：为了兼容现有同步 SQLAlchemy 服务和异步 LLMClient，服务内提供隔离线程调用路径；测试使用 fake LLM，真实 LLM 可由后续调度/环境验证覆盖。
- 合规边界：Invalid/Watch 和 C 级规则沿用现有分级硬规则，C 级自动合规复核。
- 范围控制：未执行下一 Story；未做锁操作；未做 git 操作。
- 修正结果：无需修正。

## 后续建议

下一 Story 可进入 `P2-E6-S1`，实现第二阶段 dashboard API。但本次执行未进入下一 Story。
