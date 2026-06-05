# Story P4-E3-S4：在 agent_task_runs.output_summary_json 保存 external_agent_run_id

状态：已实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为运营和排障人员，我希望 `apps/api.agent_task_runs` 能保存 `apps/agents` 返回的外部 run id，以便第四阶段在不改表结构的前提下追踪一次 HTTP Agent 调用。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `agent_task_runs.output_summary_json` 中保存 `external_agent_run_id`、`external_agent_status`、`agents_base_url` 等兼容摘要。

**建议文件：**

- Modify: `apps/api/app/services/`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/agents/test_agent_task_run_external_summary.py`

**验收标准：**

- 不修改 `agent_task_runs` 表结构。
- HTTP Agent 调用成功创建外部 run 后，`output_summary_json.external_agent_run_id` 可追踪。
- 失败时记录可排障摘要，但不吞掉原始错误语义。
- 摘要字段不包含 API Key 或敏感输入全文。

**非目标：**

- 不删除 `apps/api` retry worker。
- 不迁移历史 `agent_task_runs`。
- 不让 `apps/api` 成为 `apps/agents` 的运行状态事实源。

## Codex 提示词

```text
请执行 P4-E3-S4：在 agent_task_runs.output_summary_json 保存 external_agent_run_id。
要求使用 TDD；不得修改 agent_task_runs 表结构；不得记录 API Key；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api.agent_task_runs` 第四阶段只做兼容摘要。
- `apps/agents` 是 Agent 执行事实源。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 执行记录

执行日期：2026-06-05  
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md` 执行当前 Story。

### Git / Worktree 记录

- 延续当前环境事实：沙箱禁止写 `.git/FETCH_HEAD` 和 `.git/refs/heads/*.lock`。
- 无法在本环境完成 `git fetch`、创建分支和 worktree。
- 按当前目标的 sandbox fallback，在当前工作区继续执行本 Story。
- 未执行 git 提交。

### TDD 记录

红灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_agent_task_run_external_summary.py -q
```

结果：`3 failed`，原因是 `AgentTaskRunService` 尚无 `succeed_with_external_agent_summary` 和 `fail_with_external_agent_summary`。

实现后第一次运行：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_agent_task_run_external_summary.py -q
```

结果：`2 passed, 1 failed`。失败原因是外部 audit 扩展字段 `api_key` 未脱敏。

修正：

- 外部 audit 扩展字段按 key 判断是否敏感。
- 将 `api_key` 等敏感字段写为 `[REDACTED]`。

第一轮评审补充测试后发现：

- `raw_text` 这类非公开全文输入字段也不能进入兼容摘要。

修正：

- 将 `body`、`content`、`html`、`page_text`、`raw_text`、`source_text`、`text` 加入敏感摘要 key。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_agent_task_run_external_summary.py -q
```

结果：`3 passed in 0.62s`。

### 实现摘要

- 在 `apps/api/app/services/agent_task_runs.py` 中新增 `succeed_with_external_agent_summary`。
- 在 `apps/api/app/services/agent_task_runs.py` 中新增 `fail_with_external_agent_summary`。
- 在 `apps/api/app/services/agent_task_runs.py` 中新增 `merge_external_agent_summary`。
- 成功摘要合并 `external_agent_run_id`、`external_agent_status`、`external_agent_type`、`external_agent_mode`、`agents_base_url`。
- 失败摘要保留原始 `error` 和 `retry_decision` 语义，并追加 `external_agent_error`。
- 外部 audit 摘要只保留可排障摘要：`writes_core_tables`、`executed_node_count`、`failed_node`、`risk_flags`、`source_url_count` 以及脱敏后的扩展摘要字段。
- 不保存 API Key、token、password、authorization、cookie 等敏感字段。
- 不保存 `input_json`、`raw_text`、`source_text`、`page_text`、`html`、`content`、`body` 等非公开输入全文。
- 未修改 `agent_task_runs` 表结构。
- 未删除 `apps/api` retry worker。
- 未迁移历史 `agent_task_runs`。
- 未让 `apps/api` 成为 `apps/agents` 的运行状态事实源。

### 验证命令

当前 Story 测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_agent_task_run_external_summary.py -q
```

结果：`3 passed in 0.62s`。

`apps/api` 聚焦回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_agent_task_run_external_summary.py tests/test_agent_task_run_model.py tests/agents/test_http_agent_runtime.py tests/agents/test_http_runtime_compatibility.py tests/test_agents_settings.py tests/test_llm_settings.py tests/test_llm_client.py -q
```

结果：`31 passed in 0.72s`。

`apps/api` 导入与方法检查：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.main import app
from app.services.agent_task_runs import AgentTaskRunService
print(app.title)
print(len(app.routes) > 0)
print(hasattr(AgentTaskRunService, 'succeed_with_external_agent_summary'))
print(hasattr(AgentTaskRunService, 'fail_with_external_agent_summary'))
PY
```

执行目录：`apps/api`  
结果：

```text
Overseas Vehicle Leads AI API
True
True
True
```

`apps/agents` 回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

执行目录：`apps/agents`  
结果：`49 passed in 0.50s`。

## 两轮独立评审记录

### 第一轮评审：验收标准、表结构和敏感信息

结论：

- 通过。未修改 `agent_task_runs` 迁移，未新增 `external_agent_run_id` 或 `external_agent_status` 列。
- 通过。HTTP Agent 成功创建外部 run 后，可通过 `output_summary_json.external_agent_run_id` 追踪。
- 通过。失败时保留 `error` 和 `retry_decision`，没有吞掉原始错误语义。
- 通过。摘要字段不包含 API Key 或 token。
- 通过。`apps/api.agent_task_runs` 只做兼容摘要，`apps/agents` 仍是执行事实源。

发现项：

- 初版脱敏覆盖了 API Key 和 token，但没有覆盖 `raw_text` 等可能包含非公开输入全文的字段。

修正结果：

- 已将全文输入相关 key 加入脱敏列表。
- 已补充测试断言 `private lead page body` 不会进入 `output_summary_json`。

### 第二轮评审：回归风险、可排障性和职责边界

结论：

- 通过。成功摘要保留外部 run id、状态、类型、模式和 agents base URL，满足排障追踪。
- 通过。失败摘要保留外部错误对象和失败节点摘要，便于后续失败案例整理。
- 通过。外部 audit 只保存节点数量和 URL 数量，不保存 source URLs 全文列表。
- 通过。未删除或改动 `apps/api` retry worker。
- 通过。未迁移历史 `agent_task_runs`。
- 通过。`apps/api` 聚焦回归通过：`31 passed in 0.72s`。
- 通过。`apps/agents` 回归通过：`49 passed in 0.50s`。

发现项：

- 当前 Story 只提供兼容摘要合并能力，尚未把 HTTP runtime 调用结果接入具体业务 task run 写入流程。

修正结果：

- 无需在本 Story 扩展；具体业务消费和写入属于后续 active_run / result consumption Story。
