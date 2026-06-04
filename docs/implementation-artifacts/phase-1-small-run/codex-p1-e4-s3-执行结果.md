# P1-E4-S3 执行结果

Story：`docs/stories/phase-1-small-run/P1-E4-S3-llm-lead-extraction.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、TDD、定向回归、编译检查和 Story 状态回写；真实 PostgreSQL/Redis 联调验证受当前沙箱出网限制影响，待可出网环境复验

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施计划、`prompts/lead-extraction.md`、`docs/poc/ai-output-schema.md` 和 superpowers TDD/verification 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/app/services/llm_lead_extraction.py`
- `apps/api/app/schemas/llm_lead_extraction.py`
- `apps/api/app/api/llm_lead_extraction.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_llm_lead_extraction.py`
- `docs/stories/phase-1-small-run/P1-E4-S3-llm-lead-extraction.md`
- `_bmad-output/implementation-artifacts/codex-p1-e4-s3-执行结果.md`

## 3. 实现内容

### 3.1 LLM 抽取验收服务

新增 `LLMLeadExtractionService`，作为 LLM 输出进入 staging 前的强校验边界。

核心能力：

- 按 `lead_extraction_output` 结构规范化 LLM JSON
- 缺失字段统一为 `Unknown`、`null` 或 `[]`
- 校验 `schema_version`、`task_type`
- 校验 `source_url` 必须与候选 URL 一致
- 校验 `customer_type` 枚举
- 校验来源证据必须存在，且每条证据的 `source_url` 与候选来源一致
- 校验联系方式必须出现在公开文本摘要中，不允许 AI 编造联系方式
- Low/Medium 通过后写入 `staging_leads`
- High/Forbidden 不写入 staging，仅记录审计
- 每次成功或失败均写入 `ai_audit_logs`

### 3.2 Staging 写入策略

由于本 Story 只负责“抽取”，不负责“分级”，写入 staging 时采用保守默认：

- `recommended_grade=Watch`
- `recommended_reason=等待 LLM 分级校验；本任务仅完成公开文本抽取。`
- `queue_status` 由既有 `StagingLeadService.default_queue_status` 自动保持不可触达

后续 `P1-E4-S4` 负责分级和规则校验后，再决定是否进入 B/C 交付路径。

### 3.3 API

新增：

```text
POST /llm-lead-extraction/run
```

请求：

```json
{
  "candidate_url_id": "uuid",
  "llm_output_json": {}
}
```

说明：

- 当前实现不硬编码具体模型 provider。
- 外部 Agent 或后续模型适配层调用 `lead-extraction` prompt 后，将 JSON 输出提交给本 API 校验和落库。
- 任何 provider 都不能绕过本服务的 schema、来源、证据和联系方式校验。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 调用 lead extraction prompt | 通过 | 服务固定使用 `lead-extraction-v1` prompt version；API 接收该 prompt 产出的 JSON |
| 输出符合 schema 的 JSON | 通过 | `validate_extraction_output` 校验 schema/task/source/evidence/enums |
| 写入 staging_leads | 通过 | `run_extraction` 调用 `StagingLeadService.create_staging_lead` |
| 写入 ai_audit_logs | 通过 | 成功和失败路径均调用 `AuditRiskLogService.record_ai_audit` |
| 输出包含客户名称、国家、城市、客户类型、联系方式、经营信号、来源证据 | 通过 | `build_staging_payload` 映射所有字段 |
| 缺失字段为 Unknown/null/[] | 通过 | `normalize_extraction_output` |
| 不允许编造联系方式 | 通过 | 联系方式必须出现在公开文本摘要中 |
| schema 校验失败不得写入 staging | 通过 | 校验异常发生在 `create_staging_lead` 前 |
| schema 校验失败需记录失败案例 | 部分通过 | 失败路径写入 `ai_audit_logs`，正式 `failed_cases` 表/集合由 P1-E4-S5 承接 |
| 不做自动触达 | 通过 | 默认 Watch，不进入触达队列 |
| 每条抽取结果必须关联 source_url 和 evidence_note | 通过 | source_url 一致性与 source_evidence 必填校验 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_lead_extraction.py -q
```

结果：

```text
ERROR ModuleNotFoundError: No module named 'app.services.llm_lead_extraction'
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_lead_extraction.py -q
```

结果：

```text
5 passed in 0.27s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/llm_lead_extraction.py apps/api/app/schemas/llm_lead_extraction.py apps/api/app/api/llm_lead_extraction.py apps/api/app/main.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_lead_extraction.py apps/api/tests/test_public_page_read_agent.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_channel_discovery_agent.py -q
```

结果：

```text
45 passed in 1.31s
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0016 (head)
```

## 6. 两轮独立评审

### 6.1 第一轮：Schema、证据和反编造评审

结论：通过。

发现项：

- LLM 输出不能因为 JSON 形状正确就直接写 staging；联系方式必须可在公开文本中找到。
- source evidence 不仅要存在，还必须引用同一个候选来源 URL。
- 抽取阶段不能提前把线索送入触达队列。

修正结果：

- 增加联系方式来源文本校验。
- 增加 source_url 一致性和 evidence 必填校验。
- staging 默认写入 `Watch`，等待 P1-E4-S4 分级后再决定下一步。

### 6.2 第二轮：实现、审计和失败路径评审

结论：通过，存在真实数据库/Redis 联调环境残留验证项。

发现项：

- schema invalid、risk blocked、疑似编造等失败路径不能静默失败，必须有审计记录。
- 当前没有正式 `failed_cases` 表，不能在本 Story 临时扩表。
- 当前 Codex 沙箱无法连接真实 PostgreSQL/Redis。

修正结果：

- 失败路径调用 `record_ai_audit`，设置 `risk_blocked=True` 与 `risk_block_reason`。
- 未新增 migration，把正式失败案例库留给 P1-E4-S5。
- 将真实库验证阻塞原因记录为残留风险。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL/Redis，`POST /llm-lead-extraction/run` 的真实库写入需在可出网环境复验。
- 真实模型 provider 尚未接入；当前 Story 完成的是 prompt 输出验收、风控校验和落库边界，后续可在不绕过校验的前提下接 OpenAI/Claude/本地模型。
- 联系方式校验目前要求文本中出现完整字符串，可能会拦截格式差异较大的真实电话号码，后续可在保持“不编造”原则下增加电话号码标准化匹配。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E4-S4-llm-grading-rule-validation.md`

