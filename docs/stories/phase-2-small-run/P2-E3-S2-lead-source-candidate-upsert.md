# Story P2-E3-S2：实现来源候选 upsert、去重和默认审核状态服务

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P2-E3

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现来源候选 upsert、去重和默认审核状态服务”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 将校验后的来源候选写入 `lead_source_candidates`，处理重复和风险默认状态。

**Files:**

- Create: `apps/api/app/services/lead_source_candidates.py`
- Test: `apps/api/tests/test_lead_source_candidate_upsert.py`

**Codex 提示词：**

```text
请执行 P2-E3-S2：实现来源候选 upsert、去重和默认审核状态服务。

要求：
1. 使用 superpowers:test-driven-development。
2. 按 source_url 或 normalized_domain + platform 生成 dedupe_key。
3. 重复来源不自动删除，标记 is_duplicate 或 duplicate_of_id。
4. Low/Medium 自动 auto_approved + approved_for_extraction=true。
5. High 自动 high_risk_review + approved_for_extraction=false。
6. Forbidden 自动 rejected + approved_for_extraction=false。
7. 写入 created_by_task_run_id，保留 llm_output_json 和 evidence_links。
8. 运行 pytest apps/api/tests/test_lead_source_candidate_upsert.py。
9. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e3-s2-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 来源可 upsert。
- 重复可标记。
- 风险默认状态正确。

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

执行日期：2026-06-02

已完成：

- 新增 `apps/api/app/services/lead_source_candidates.py`。
- 新增 `apps/api/tests/test_lead_source_candidate_upsert.py`。
- 实现 `LeadSourceCandidateService.upsert_candidate`。
- 实现 `LeadSourceCandidateService.upsert_from_source_discovery_output`。
- 按 `source_url + normalized_domain + platform` 生成 `dedupe_key`。
- 同一 `dedupe_key` 重复来源走幂等更新，不新增重复记录。
- 同一 `normalized_domain + platform` 但 URL 不同的来源新增记录，并标记：
  - `is_duplicate=true`
  - `duplicate_of_id=<首条同域同平台来源 id>`
- Low/Medium 默认：
  - `review_status=auto_approved`
  - `approved_for_extraction=true`
  - `extraction_status=pending`
- High 默认：
  - `review_status=high_risk_review`
  - `approved_for_extraction=false`
  - `extraction_status=pending`
- Forbidden 默认：
  - `review_status=rejected`
  - `approved_for_extraction=false`
  - `extraction_status=blocked`
- 写入并保留：
  - `created_by_task_run_id`
  - `llm_output_json`
  - `llm_provider`
  - `llm_model`
  - `evidence_links`
- 修正 `LeadSourceCandidate` 和 `AgentTaskRun` 时间默认值为时区感知 UTC，避免真实 PostgreSQL 写入测试触发 `datetime.utcnow()` 弃用警告。

未执行：

- 未实现来源候选查询 API。
- 未实现来源审核 API。
- 未实现 Source Discovery Agent。
- 未实现移动端页面。
- 未执行 P2-E3-S3 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_upsert.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.lead_source_candidates'
```

失败原因符合预期：来源候选 upsert 服务尚未实现。

GREEN：

- 新增 `LeadSourceCandidateService`。
- 复用 `LeadSourceCandidateRules.resolve_defaults` 和 `build_dedupe_key`。
- 实现单条 upsert 和 Source Discovery 输出批量 upsert。
- 首次实现后发现批量测试中 blocked 来源未标记重复，根因是测试样例未携带相同 platform，导致不满足 `normalized_domain + platform` 重复规则；已修正测试样例。
- 修正 `LeadSourceCandidate` 和 `AgentTaskRun` UTC 时间默认值。

## 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_upsert.py -q
```

结果：

```text
7 passed in 8.05s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidate_upsert.py apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_lead_source_candidate_model.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_agent_task_run_model.py -q
```

结果：

```text
39 passed in 7.75s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/lead_source_candidates.py apps/api/app/models/lead_source_candidate.py apps/api/app/models/agent_task_run.py apps/api/tests/test_lead_source_candidate_upsert.py
```

结果：通过，退出码 0。

## 两轮独立评审记录

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
