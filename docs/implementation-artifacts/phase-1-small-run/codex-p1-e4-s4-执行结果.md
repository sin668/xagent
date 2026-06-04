# P1-E4-S4 执行结果

Story：`docs/stories/phase-1-small-run/P1-E4-S4-llm-grading-rule-validation.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、TDD、定向回归、编译检查和 Story 状态回写；真实 PostgreSQL/Redis 联调验证受当前沙箱出网限制影响，待可出网环境复验

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施计划、`prompts/lead-grading.md`、`docs/poc/ai-output-schema.md` 和 superpowers TDD/verification 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/app/services/llm_lead_grading.py`
- `apps/api/app/schemas/llm_lead_grading.py`
- `apps/api/app/api/llm_lead_grading.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_llm_lead_grading.py`
- `docs/stories/phase-1-small-run/P1-E4-S4-llm-grading-rule-validation.md`
- `_bmad-output/implementation-artifacts/codex-p1-e4-s4-执行结果.md`

## 3. 实现内容

### 3.1 LLM 分级服务

新增 `LLMLeadGradingService`，作为 LLM 分级建议进入 staging 状态更新前的硬规则校验边界。

核心能力：

- 校验 `lead_grading_output` 的 `schema_version`、`task_type`
- 校验 `recommended_grade`、`next_action`、`suggested_handoff_team` 枚举
- 校验 `evidence_refs` 必须存在，且 `source_url` 与候选来源一致
- 结合渠道风险、复核状态、联系方式、来源证据、勿扰状态执行硬规则
- 更新 `staging_leads.recommended_grade`
- 更新 `staging_leads.recommended_reason`
- 更新 `staging_leads.missing_fields`
- 更新 `staging_leads.queue_status`
- 更新 `staging_leads.requires_compliance_review`
- 写入 `ai_audit_logs`
- 将 `rule_validation_result` 写入 AI 审计输出

### 3.2 硬规则覆盖 LLM 建议

已实现：

- Invalid / Watch 强制 `queue_status=not_eligible`
- A 级强制不进入触达队列，保留补全/复核
- B / C 在 Low/Medium、证据和联系方式齐全且 LLM 允许人工触达时可进入 `eligible`
- High / Forbidden 强制 `queue_status=blocked`
- High 二次复核未完成强制阻断
- C 级强制 `requires_compliance_review=true`
- C 级强制追加 `c_grade_requires_compliance_review`
- 缺来源证据强制 `not_eligible`
- 缺联系方式不得进入 eligible
- 勿扰客户强制 `not_eligible`

### 3.3 API

新增：

```text
POST /llm-lead-grading/run
```

请求：

```json
{
  "staging_lead_id": "uuid",
  "llm_output_json": {},
  "do_not_contact": false
}
```

响应包含：

- `staging_lead`
- `rule_validation_result`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 调用 lead grading prompt | 通过 | 服务固定使用 `lead-grading-v1` prompt version；API 接收该 prompt 产出的 JSON |
| 结合规则校验渠道风险、联系方式、证据、勿扰、C 级复核 | 通过 | `apply_hard_rules` |
| 更新 staging_leads 推荐等级和 queue_status | 通过 | `run_grading` 更新 staging lead |
| 写入 ai_audit_logs 和 rule validation result | 通过 | `record_ai_audit` 的 `output_json.rule_validation_result` |
| Invalid/Watch queue_status 必须 not_eligible | 通过 | 测试覆盖 |
| High 未二次复核 queue_status 必须 blocked 或 needs_secondary_verification | 通过 | 当前队列枚举无 needs_secondary_verification，统一 `blocked` |
| C 级 requires_compliance_review=true | 通过 | 测试覆盖 |
| 推荐原因必须引用证据 | 通过 | `evidence_refs` 必填且 source_url 一致 |
| 不做黑箱评分模型 | 通过 | 仅验收 LLM 建议并套硬规则 |
| LLM 推荐不得覆盖硬规则阻断 | 通过 | 硬规则最终决定 `queue_status` 和 `touch_queue_allowed` |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_lead_grading.py -q
```

结果：

```text
ERROR ModuleNotFoundError: No module named 'app.services.llm_lead_grading'
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_lead_grading.py -q
```

结果：

```text
6 passed in 0.35s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/llm_lead_grading.py apps/api/app/schemas/llm_lead_grading.py apps/api/app/api/llm_lead_grading.py apps/api/app/main.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_lead_grading.py apps/api/tests/test_llm_lead_extraction.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_staging_review_filters.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_audit_risk_logs_foundation.py -q
```

结果：

```text
40 passed in 0.82s
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0016 (head)
```

曾尝试把 `test_customer_dnc_service.py` 纳入相关回归，结果该文件需要连接 `.env` 中真实 PostgreSQL，当前沙箱对 `8.129.17.71:5432` 返回 `PermissionError: [Errno 1] Operation not permitted`，因此未作为本 Story 有效回归证据。

## 6. 两轮独立评审

### 6.1 第一轮：分级规则和风控评审

结论：通过。

发现项：

- LLM 输出的 `touch_queue_allowed=true` 不能直接决定队列状态。
- C 级即使模型漏掉 `compliance_review_required`，系统也必须强制补齐。
- High/Forbidden 来源即使模型建议 B/C，也不能进入触达队列。

修正结果：

- `apply_hard_rules` 统一产出最终 `queue_status`。
- C 级强制 `requires_compliance_review=true` 和 `c_grade_requires_compliance_review`。
- High/Forbidden 强制 `blocked`，并写入风险标记。

### 6.2 第二轮：审计、数据更新和失败路径评审

结论：通过，存在真实数据库/Redis 联调环境残留验证项。

发现项：

- 推荐原因必须有证据引用，否则就是不可解释分级。
- 勿扰状态必须在分级时作为硬规则输入，而不是只依赖后续触达阶段。
- 当前 Codex 沙箱无法连接真实 PostgreSQL/Redis。

修正结果：

- `validate_grading_output` 强制 `evidence_refs` 存在且来源 URL 一致。
- API 增加 `do_not_contact` 输入，硬规则强制 `not_eligible`。
- 将真实库验证阻塞原因记录为残留风险。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL/Redis，`POST /llm-lead-grading/run` 的真实库写入需在可出网环境复验。
- `do_not_contact` 当前作为 API 输入参与分级硬规则；未来 staging 与 core 客户映射更稳定后，可自动联查 core DNC 状态。
- C 级仅标记合规复核，不代表可报价、可签约或可成交。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E4-S5-agent-failed-case-library.md`

