# P2-E3-S2 执行结果：实现来源候选 upsert、去重和默认审核状态服务

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E3-S2-lead-source-candidate-upsert.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E3-S2，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/services/lead_source_candidates.py`。
- 创建 `apps/api/tests/test_lead_source_candidate_upsert.py`。
- 实现来源候选单条 upsert。
- 实现 Source Discovery 输出批量 upsert。
- 实现同 URL/domain/platform 幂等更新。
- 实现同 domain/platform 不同 URL 疑似重复标记。
- 实现 Low/Medium/High/Forbidden 默认审核和抽取状态。
- 保留 `created_by_task_run_id`、`llm_output_json`、`llm_provider`、`llm_model`、`evidence_links`。
- 修正 `LeadSourceCandidate` 与 `AgentTaskRun` 时间默认值为时区感知 UTC。

未执行：

- 未实现来源候选查询 API。
- 未实现来源审核 API。
- 未实现 Source Discovery Agent。
- 未实现移动端页面。
- 未执行 P2-E3-S3 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/services/lead_source_candidates.py`
- `apps/api/app/models/lead_source_candidate.py`
- `apps/api/app/models/agent_task_run.py`
- `apps/api/tests/test_lead_source_candidate_upsert.py`
- `docs/stories/phase-2-small-run/P2-E3-S2-lead-source-candidate-upsert.md`
- `_bmad-output/implementation-artifacts/codex-p2-e3-s2-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_upsert.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.lead_source_candidates'
```

失败原因：来源候选 upsert 服务尚未实现，符合当前 Story 的 RED 预期。

GREEN：

- 新增 `LeadSourceCandidateService`。
- 复用 `LeadSourceCandidateRules.resolve_defaults` 和 `build_dedupe_key`。
- 实现单条 upsert 和 Source Discovery 输出批量 upsert。
- 首次实现后发现批量测试中 blocked 来源未标记重复，根因是测试样例未携带相同 platform，导致不满足 `normalized_domain + platform` 重复规则；已修正测试样例。
- 修正 `LeadSourceCandidate` 和 `AgentTaskRun` UTC 时间默认值。

## 4. 验证命令与结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_upsert.py -q
```

结果：

```text
7 passed in 8.05s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_upsert.py apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_agent_task_run_model.py -q
```

结果：

```text
39 passed in 7.75s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/lead_source_candidates.py apps/api/app/models/lead_source_candidate.py apps/api/app/models/agent_task_run.py apps/api/tests/test_lead_source_candidate_upsert.py
```

结果：通过，退出码 0。

## 5. 验收结果

- 来源可 upsert。
- 重复来源不自动删除。
- 同 URL/domain/platform 走幂等更新。
- 同 domain/platform 不同 URL 标记 `is_duplicate=true` 和 `duplicate_of_id`。
- Low/Medium 默认 `auto_approved + approved_for_extraction=true`。
- High 默认 `high_risk_review + approved_for_extraction=false`。
- Forbidden 默认 `rejected + approved_for_extraction=false + extraction_status=blocked`。
- 写入 `created_by_task_run_id`，保留 `llm_output_json` 和 `evidence_links`。

## 6. 风控结果

- 未调用真实 LLM。
- 未实现自动抽取。
- 未实现客户触达。
- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- High/Forbidden 风险边界未被放宽。

## 7. 双轮评审记录

### 第一轮评审：Story 范围与数据写入契约

结论：通过。

发现项：

- 来源可 upsert 到 `lead_source_candidates`。
- 同 URL/domain/platform 来源幂等更新，不新增重复记录。
- 同 domain/platform 不同 URL 来源会新增并标记 `is_duplicate/duplicate_of_id`，不自动删除。
- `created_by_task_run_id`、`llm_output_json`、`evidence_links` 均被保留。
- 本 Story 未越界实现查询 API、审核 API、Agent 或移动端。

修正结果：

- 已修正批量 blocked 来源测试样例，使其准确覆盖同 domain/platform 不同 URL 的重复规则。

### 第二轮评审：风险默认状态、审计与合规边界

结论：通过。

发现项：

- Low/Medium 默认自动通过并允许抽取。
- High 默认进入高风险复核，不允许抽取。
- Forbidden 默认驳回并阻断抽取。
- 目标测试 7 条通过，相关回归测试 39 条通过。
- Python 编译通过。
- 未触发自动社交私信、加好友、登录后批量采集、反爬规避或非公开数据抓取。

修正结果：

- 已将 `LeadSourceCandidate` 和 `AgentTaskRun` 的 `created_at/updated_at` 默认值调整为 `datetime.now(UTC)`。
