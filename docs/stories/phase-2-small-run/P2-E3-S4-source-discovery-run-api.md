# Story P2-E3-S4：实现 Source Discovery 手动启动 API 和任务审计

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P2-E3

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现 Source Discovery 手动启动 API 和任务审计”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 提供移动端/后台可调用的手动启动接口。

**Files:**

- Create: `apps/api/app/api/source_discovery_agent.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_source_discovery_agent_api.py`

**Codex 提示词：**

```text
请执行 P2-E3-S4：实现 Source Discovery 手动启动 API 和任务审计。

要求：
1. 使用 superpowers:test-driven-development。
2. 新增 POST /agent-tasks/source-discovery/run。
3. 请求参数包括 country、cities、channel_strategy、keywords、limit。
4. limit 必须受第二阶段配额限制，单次默认 20-50。
5. API 返回 agent_task_run_id、status、created_count、blocked_count、duplicate_count。
6. 不提供自动触达入口。
7. 运行 pytest apps/api/tests/test_source_discovery_agent_api.py。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e3-s4-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 手动启动 API 可创建任务并返回结果摘要。
- 审计记录完整。

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

- 新增 `apps/api/app/api/source_discovery_agent.py`。
- 新增 `apps/api/app/schemas/source_discovery_agent.py`。
- 新增 `apps/api/tests/test_source_discovery_agent_api.py`。
- 修改 `apps/api/app/main.py`，注册 `source_discovery_agent_router`。
- 修改 `apps/api/app/services/source_discovery_agent.py`，在 `SourceDiscoveryAgentResult` 和任务摘要中补充 `blocked_count`。
- 修改 `apps/api/app/services/lead_source_candidates.py`，在批处理结果中按 Forbidden 来源计算 `blocked_count`。
- 修改 `apps/api/tests/test_phase2_data_foundation.py`，移除已过期的“Source Discovery Agent 服务不得存在”断言，保留“来源候选 API 尚未定义”的边界。

接口能力：

- 新增 `POST /agent-tasks/source-discovery/run`。
- 请求参数包含：
  - `country`
  - `cities`
  - `channel_strategy`
  - `keywords`
  - `limit`
- `limit` 按第二阶段单次配额限制为 `20 <= limit <= 50`，默认 `20`。
- API 将 `cities` 转换为 Agent 输入中的城市字符串。
- API 调用 `SourceDiscoveryAgentService.run`，触发来源发现任务。
- API 返回：
  - `agent_task_run_id`
  - `status`
  - `created_count`
  - `blocked_count`
  - `duplicate_count`

未执行：

- 未实现定时任务。
- 未实现来源候选列表/详情 API。
- 未实现来源审核 API。
- 未实现客户抽取 API 变更。
- 未实现客户触达、私信、加好友或短信入口。
- 未执行 P2-E3-S5 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent_api.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.api.source_discovery_agent'
```

失败原因符合预期：Source Discovery 手动启动 API 模块尚未创建。

GREEN：

- 新增 API schema，约束 `limit` 为 20-50。
- 新增 FastAPI router：`/agent-tasks/source-discovery/run`。
- 为 API 提供可覆盖的 `get_source_discovery_service` 依赖，目标测试使用 mock service，避免测试触发真实 LLM。
- 注册 router 到 `app.main`。
- 在来源候选批处理和 Agent result 中补充 `blocked_count`，保证 API 摘要来自服务层审计结果。
- 修正过期阶段底座契约测试：`P2-E3-S3` 已交付 `source_discovery_agent.py`，不应继续断言该服务不存在。

## 验证结果

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

## 两轮独立评审记录

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
