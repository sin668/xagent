# Story P2-E3-S5：实现来源候选列表、详情、筛选 API

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P2-E3

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现来源候选列表、详情、筛选 API”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 支撑移动端来源候选队列和来源详情页。

**Files:**

- Create: `apps/api/app/api/lead_source_candidates.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_lead_source_candidates_query_api.py`

**Codex 提示词：**

```text
请执行 P2-E3-S5：实现来源候选列表、详情、筛选 API。

要求：
1. 使用 superpowers:test-driven-development。
2. 提供 GET /lead-source-candidates 和 GET /lead-source-candidates/{id}。
3. 支持 risk_level、review_status、country、city、platform、channel_name、extraction_status 筛选。
4. 列表返回 URL/domain、风险、状态、证据摘要、是否可抽取、最近发现时间。
5. 详情返回 LLM 输出摘要、evidence_links、created_by_task_run_id。
6. 运行 pytest apps/api/tests/test_lead_source_candidates_query_api.py。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e3-s5-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 移动端可读取来源候选队列和详情。
- 筛选条件可用。

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

- 新增 `apps/api/app/api/lead_source_candidates.py`。
- 新增 `apps/api/tests/test_lead_source_candidates_query_api.py`。
- 修改 `apps/api/app/main.py`，注册 `lead_source_candidates_router`。
- 修改 `apps/api/app/schemas/lead_source_candidate.py`，补充列表分页字段和详情响应 `llm_output_summary`。
- 修改 `apps/api/app/services/lead_source_candidates.py`，新增来源候选列表查询、筛选、分页和详情查询。
- 修改 `apps/api/tests/test_phase2_data_foundation.py`，将过期的“来源候选 API 不应存在”断言调整为“来源候选 API 保持只读 GET”。

接口能力：

- 新增 `GET /lead-source-candidates`。
- 新增 `GET /lead-source-candidates/{candidate_id}`。
- 列表支持筛选：
  - `risk_level`
  - `review_status`
  - `country`
  - `city`
  - `platform`
  - `channel_name`
  - `extraction_status`
- 列表支持分页：
  - `limit`，默认 100，范围 1-500
  - `offset`，默认 0
- 列表返回 URL/domain、风险、状态、证据摘要、是否可抽取、创建时间等来源候选队列字段。
- 详情返回 `evidence_links`、`created_by_task_run_id`、`llm_output_json` 和 `llm_output_summary`。

未执行：

- 未实现来源审核动作 API。
- 未实现来源候选写入 API。
- 未实现自动抽取。
- 未实现客户触达、私信、加好友或短信入口。
- 未执行 P2-E3-S6 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidates_query_api.py -q
```

结果：

```text
404 Not Found
KeyError: '/lead-source-candidates'
```

失败原因符合预期：来源候选查询 API 尚未创建。

GREEN：

- 新增目标测试，覆盖列表筛选、详情、分页、404 和只读边界。
- 新增只读 FastAPI router。
- 新增 service 查询方法，统一处理筛选、分页和详情查询。
- 详情响应增加 `llm_output_summary`，用于移动端展示 LLM 输出摘要。
- 回归时发现阶段底座契约测试仍断言来源候选 API 不存在；该断言随 P2-E3-S5 推进已过期，已改为验证 API 仅包含 GET，不包含 POST/PATCH/DELETE。

## 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidates_query_api.py -q
```

结果：

```text
5 passed in 7.54s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidates_query_api.py apps/api/tests/test_lead_source_candidate_upsert.py apps/api/tests/test_source_discovery_agent.py apps/api/tests/test_source_discovery_agent_api.py apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_phase2_data_foundation.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_agent_task_run_model.py -q
```

结果：

```text
52 passed in 21.96s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/api/lead_source_candidates.py apps/api/app/schemas/lead_source_candidate.py apps/api/app/services/lead_source_candidates.py apps/api/tests/test_lead_source_candidates_query_api.py apps/api/tests/test_phase2_data_foundation.py
```

结果：通过，退出码 0。

完成前补充验证说明：

- 曾将目标测试和包含目标测试的回归集并行执行，因两组测试使用相同 `p2e3s5` 清理前缀，出现测试进程相互清理和重复写入，表现为 `created_by_task_run_id` 不一致、`dedupe_key` 唯一键冲突和计数变化。
- 该问题属于测试并发隔离问题，不属于查询 API 业务逻辑失败。
- 已按顺序重新执行目标测试和相关回归，结果分别为 `5 passed` 和 `52 passed`。

## 两轮独立评审记录

### 第一轮评审：API 契约、筛选和移动端队列需求

结论：通过。

发现项：

- `GET /lead-source-candidates` 已注册，可用于移动端来源候选队列。
- `GET /lead-source-candidates/{candidate_id}` 已注册，可用于移动端来源详情页。
- 筛选字段覆盖 Story 要求的 `risk_level/review_status/country/city/platform/channel_name/extraction_status`。
- 列表返回来源 URL、domain、风险、审核状态、证据摘要、是否可抽取、创建时间等队列核心字段。
- 详情返回 `evidence_links`、`created_by_task_run_id`、`llm_output_json` 和 `llm_output_summary`。

修正结果：

- 已补充 `total/limit/offset`，方便移动端分页。
- 已补充 `llm_output_summary`，避免详情页必须解析完整 LLM JSON 才能展示摘要。

### 第二轮评审：只读边界、合规和回归风险

结论：通过。

发现项：

- 当前 API 只包含 GET，不包含 POST/PATCH/DELETE。
- 未新增来源审核动作，未提前执行 P2-E3-S6。
- 未新增自动抽取、触达、私信、加好友或短信入口。
- 目标测试 5 条通过，相关回归测试 52 条通过。
- Python 编译通过。
- `test_phase2_data_foundation.py` 中旧断言已随 Story 推进修正为只读 API 边界校验。
- 并行运行同前缀数据库测试会产生清理冲突；当前完成验证已采用顺序执行。

修正结果：

- 第二轮未发现新增实质阻塞问题，无需追加业务代码修正。
