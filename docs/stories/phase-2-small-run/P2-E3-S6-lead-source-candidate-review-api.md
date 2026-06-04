# Story P2-E3-S6：实现来源审核动作 API 与风险闸门

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P2-E3

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现来源审核动作 API 与风险闸门”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 支持移动端审核来源，并保证 High/Forbidden 不越界。

**Files:**

- Modify: `apps/api/app/api/lead_source_candidates.py`
- Modify: `apps/api/app/services/lead_source_candidates.py`
- Test: `apps/api/tests/test_lead_source_candidates_review_api.py`

**Codex 提示词：**

请执行 P2-E3-S6：实现来源审核动作 API 与风险闸门。

要求：
1. 使用 superpowers:test-driven-development。
2. 支持 approve_for_extraction、reject、mark_high_risk、pause_channel、add_review_note。
3. Forbidden 不得 approve_for_extraction。
4. High 审核通过只代表允许只读抽取，不代表允许触达。
5. 所有动作必须记录 reviewer_id、review_note、reviewed_at。
6. 审核动作必须写入 agent_task_runs 或 review/audit 记录。
7. 运行 pytest apps/api/tests/test_lead_source_candidates_review_api.py。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e3-s6-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 审核动作可用。
- Forbidden/High 风险闸门不可绕过。

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

- 修改 `apps/api/app/api/lead_source_candidates.py`，新增审核动作 endpoint。
- 修改 `apps/api/app/services/lead_source_candidates.py`，新增审核动作、风险闸门和审计写入。
- 修改 `apps/api/app/schemas/lead_source_candidate.py`，新增审核动作请求/响应 schema。
- 新增 `apps/api/tests/test_lead_source_candidates_review_api.py`。
- 修改 `apps/api/tests/test_phase2_data_foundation.py`，将阶段契约更新为允许唯一的审核动作 POST，仍禁止其他写入口和触达入口。

接口能力：

- 新增 `POST /lead-source-candidates/{candidate_id}/review-actions`。
- 支持动作：
  - `approve_for_extraction`
  - `reject`
  - `mark_high_risk`
  - `pause_channel`
  - `add_review_note`
- 请求必须包含：
  - `reviewer_id`
  - `review_note`
- 响应返回来源候选详情和 `audit_task_run_id`。

风险闸门：

- Forbidden 来源不得 `approve_for_extraction`。
- Forbidden 放行失败时保持：
  - `review_status=rejected`
  - `approved_for_extraction=false`
  - `extraction_status=blocked`
- High 来源审核通过后只表示允许只读抽取：
  - `review_status=approved`
  - `approved_for_extraction=true`
  - 不新增任何触达入口。
- `mark_high_risk` 会将来源置为 High 并进入高风险复核：
  - `risk_level=High`
  - `review_status=high_risk_review`
  - `approved_for_extraction=false`
- `reject` 和 `pause_channel` 均阻断抽取。

审计：

- 每次审核动作写入 `agent_task_runs`。
- 成功动作为 `status=succeeded`。
- Forbidden 放行失败写入 `status=failed` 并保留 `error_message`。
- `input_json` 记录 `candidate_id/action/reviewer_id/review_note`。
- `output_summary_json` 记录审核后的 `risk_level/review_status/approved_for_extraction/extraction_status`。

未执行：

- 未实现移动端页面。
- 未实现自动抽取。
- 未实现客户触达、私信、加好友或短信入口。
- 未执行 P2-E4-S1 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidates_review_api.py -q
```

结果：

```text
6 failed
404 Not Found
```

失败原因符合预期：审核动作 API 尚未实现。

GREEN：

- 新增审核动作测试，覆盖五类动作、Forbidden 风险闸门、High 只读抽取边界、必填校验、404 和审计写入。
- 新增 `LeadSourceCandidateReviewActionRequest` 和 `LeadSourceCandidateReviewActionResponse`。
- 新增 `LeadSourceCandidateService.apply_review_action`。
- 新增 `AgentTaskRun` 审计写入。
- 新增 `POST /lead-source-candidates/{candidate_id}/review-actions`。
- 回归时发现上一 Story 的“只读 API”契约测试已过期，已更新为“允许唯一审核动作 POST，仍禁止其他写入口和触达入口”。

## 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidates_review_api.py -q
```

结果：

```text
6 passed in 14.31s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidates_review_api.py apps/api/tests/test_lead_source_candidates_query_api.py apps/api/tests/test_lead_source_candidate_upsert.py apps/api/tests/test_source_discovery_agent.py apps/api/tests/test_source_discovery_agent_api.py apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_agent_task_run_model.py -q
```

结果：

```text
58 passed in 35.93s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/api/lead_source_candidates.py apps/api/app/schemas/lead_source_candidate.py apps/api/app/services/lead_source_candidates.py apps/api/tests/test_lead_source_candidates_review_api.py apps/api/tests/test_phase2_data_foundation.py
```

结果：通过，退出码 0。

## 两轮独立评审记录

### 第一轮评审：审核动作、状态变更和审计完整性

结论：通过。

发现项：

- 五个审核动作均可通过 API 执行。
- 每个动作都要求 `reviewer_id` 和 `review_note`。
- 每个动作都会更新 `reviewer_id/review_note/reviewed_at`。
- 成功审核动作会写入 `agent_task_runs`，并返回 `audit_task_run_id`。
- 审计记录包含 action、candidate_id、reviewer_id、review_note 和审核后状态摘要。

修正结果：

- 已补充 Forbidden 放行失败的审计写入，失败动作也能在 `agent_task_runs` 中追踪。

### 第二轮评审：High/Forbidden 风险闸门与合规边界

结论：通过。

发现项：

- Forbidden 来源无法被 `approve_for_extraction` 放行。
- High 来源审核通过只设置抽取准入，不新增任何触达、私信、加好友或短信入口。
- `mark_high_risk` 会强制进入 `high_risk_review` 且不允许抽取。
- `reject` 和 `pause_channel` 会阻断抽取。
- 目标测试 6 条通过，相关回归测试 58 条通过。
- Python 编译通过。
- 阶段契约测试已更新为允许审核动作 POST，但仍禁止 PATCH/DELETE 和触达入口。

修正结果：

- 第二轮未发现新增实质阻塞问题，无需追加业务代码修正。
