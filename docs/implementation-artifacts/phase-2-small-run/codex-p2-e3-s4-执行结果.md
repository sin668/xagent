# P2-E3-S4 执行结果：实现 Source Discovery 手动启动 API 和任务审计

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E3-S4-source-discovery-run-api.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E3-S4，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/api/source_discovery_agent.py`。
- 创建 `apps/api/app/schemas/source_discovery_agent.py`。
- 创建 `apps/api/tests/test_source_discovery_agent_api.py`。
- 注册 `source_discovery_agent_router` 到 `apps/api/app/main.py`。
- 补充 `SourceDiscoveryAgentResult.blocked_count`。
- 补充 `LeadSourceCandidateBatchResult.blocked_count`。
- 修正已过期的阶段底座契约测试。

未执行：

- 未实现定时任务。
- 未实现来源候选列表、详情、筛选 API。
- 未实现来源审核动作 API。
- 未实现真实联网搜索变更。
- 未实现客户抽取链路变更。
- 未实现客户触达、私信、加好友或短信入口。
- 未执行 P2-E3-S5 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/api/source_discovery_agent.py`
- `apps/api/app/schemas/source_discovery_agent.py`
- `apps/api/app/main.py`
- `apps/api/app/services/source_discovery_agent.py`
- `apps/api/app/services/lead_source_candidates.py`
- `apps/api/tests/test_source_discovery_agent_api.py`
- `apps/api/tests/test_phase2_data_foundation.py`
- `docs/stories/phase-2-small-run/P2-E3-S4-source-discovery-run-api.md`
- `_bmad-output/implementation-artifacts/codex-p2-e3-s4-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent_api.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.api.source_discovery_agent'
```

失败原因：Source Discovery 手动启动 API 模块尚未创建，符合当前 Story 的 RED 预期。

GREEN：

- 新增 API schema，约束 `limit` 为 20-50，默认 20。
- 新增 `POST /agent-tasks/source-discovery/run`。
- API 将 `cities` 转为 Agent 输入中的城市字符串。
- API 调用 `SourceDiscoveryAgentService.run`。
- API 返回 `agent_task_run_id/status/created_count/blocked_count/duplicate_count`。
- 增加可覆盖服务依赖，测试使用 mock service，不触发真实 LLM。
- 将 `blocked_count` 放到服务层结果和任务摘要中，避免 API 层硬编码。

## 4. 验证命令与结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent_api.py -q
```

结果：

```text
4 passed in 1.42s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent_api.py apps/api/tests/test_source_discovery_agent.py apps/api/tests/test_lead_source_candidate_upsert.py apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_phase2_data_foundation.py -q
```

结果：

```text
47 passed in 16.71s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/api/source_discovery_agent.py apps/api/app/schemas/source_discovery_agent.py apps/api/app/services/source_discovery_agent.py apps/api/app/services/lead_source_candidates.py apps/api/tests/test_source_discovery_agent_api.py apps/api/tests/test_phase2_data_foundation.py
```

结果：通过，退出码 0。

## 5. 验收结果

- 手动启动 API 已创建。
- API 可创建 Source Discovery 任务并返回结果摘要。
- API 返回任务 id、状态和计数摘要。
- `limit` 默认 20，范围限制 20-50。
- 审计记录仍由 `agent_task_runs` 和 Agent 服务保存。
- 没有新增自动触达入口。

## 6. 风控结果

- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- 未新增触达、私信、加好友或短信入口。
- High/Forbidden 风险边界未被放宽。

## 7. 双轮评审记录

### 第一轮评审：API 契约、配额和审计摘要

结论：通过。

发现项：

- `POST /agent-tasks/source-discovery/run` 已注册到 FastAPI。
- 请求字段覆盖 `country/cities/channel_strategy/keywords/limit`。
- `limit` 已按第二阶段单次配额限制为 20-50，默认 20。
- API 返回 `agent_task_run_id/status/created_count/blocked_count/duplicate_count`。
- API 调用服务层 `SourceDiscoveryAgentService.run`，任务审计仍由 `agent_task_runs` 保存。
- `blocked_count` 已从来源候选服务批处理结果传递到 Agent result 和 API response。

修正结果：

- 已将 `blocked_count` 从 API 层硬编码风险改为服务层计算，保证摘要与候选写入结果一致。

### 第二轮评审：合规边界、失败处理和回归风险

结论：通过。

发现项：

- 新接口只提供手动启动 Source Discovery，不提供触达、私信、加好友或短信入口。
- 目标测试使用依赖覆盖 mock service，不触发真实 LLM，避免测试不可控成本和外部调用。
- API 对缺少默认 prompt 等服务层 `ValueError` 返回 422，不静默吞掉错误。
- 相关回归测试 47 条通过。
- 编译验证通过。
- `test_phase2_data_foundation.py` 中旧断言已随 Story 推进修正，避免继续否定已完成的 P2-E3-S3 交付物。

修正结果：

- 第二轮未发现新增实质阻塞问题，无需追加业务代码修正。
