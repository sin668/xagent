# P2-E3-S5 执行结果：实现来源候选列表、详情、筛选 API

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E3-S5-lead-source-candidate-query-api.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E3-S5，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/api/lead_source_candidates.py`。
- 创建 `apps/api/tests/test_lead_source_candidates_query_api.py`。
- 注册 `lead_source_candidates_router` 到 `apps/api/app/main.py`。
- 扩展 `apps/api/app/schemas/lead_source_candidate.py`。
- 扩展 `apps/api/app/services/lead_source_candidates.py`。
- 修正随 Story 推进已过期的阶段底座契约测试。

未执行：

- 未实现来源审核动作 API。
- 未实现来源候选写入 API。
- 未实现自动抽取。
- 未实现客户触达、私信、加好友或短信入口。
- 未执行 P2-E3-S6 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/api/lead_source_candidates.py`
- `apps/api/app/schemas/lead_source_candidate.py`
- `apps/api/app/services/lead_source_candidates.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_lead_source_candidates_query_api.py`
- `apps/api/tests/test_phase2_data_foundation.py`
- `docs/stories/phase-2-small-run/P2-E3-S5-lead-source-candidate-query-api.md`
- `_bmad-output/implementation-artifacts/codex-p2-e3-s5-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_source_candidates_query_api.py -q
```

结果：

```text
404 Not Found
KeyError: '/lead-source-candidates'
```

失败原因：来源候选查询 API 尚未创建，符合当前 Story 的 RED 预期。

GREEN：

- 新增目标测试，覆盖列表筛选、详情、分页、404 和只读边界。
- 新增只读 FastAPI router。
- 新增 service 查询方法，统一处理筛选、分页和详情查询。
- 详情响应增加 `llm_output_summary`。
- 将阶段底座契约测试从“API 不存在”更新为“API 只读 GET”。

## 4. 验证命令与结果

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

## 5. 验收结果

- 移动端可读取来源候选队列。
- 移动端可读取来源详情。
- 筛选条件可用。
- 详情包含证据链接和任务审计关联。
- API 保持只读，不提供审核动作或写入入口。

## 6. 风控结果

- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- 未新增自动抽取入口。
- 未新增触达、私信、加好友或短信入口。
- High/Forbidden 风险边界未被放宽。

## 7. 双轮评审记录

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
