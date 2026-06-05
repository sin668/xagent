# Story P4-E3-S1：新增 apps/api 调用 apps/agents 的配置

状态：已实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为 `apps/api` 的维护者，我希望通过配置声明 `apps/agents` 的服务地址、内部 API Key 和超时，以便 `apps/api` 可以通过 HTTP 调用独立 Agent 服务，而不把 `apps/agents` 作为本地包注入。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `apps/api` 配置体系中新增 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS`，默认指向本地 `apps/agents:8010`。

**建议文件：**

- Modify: `apps/api/app/core/config.py`
- Modify: `apps/api/.env.example`
- Modify: `apps/api/README.md`
- Test: `apps/api/tests/test_agents_settings.py`

**验收标准：**

- `apps/api` 可读取 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS`。
- 本地默认地址使用 `http://localhost:8010` 或项目约定的等价地址。
- 未配置 API Key 时，调用端应显式失败或禁用 HTTP Agent runtime，不静默降级。
- 配置变更不影响 `apps/api` 现有 LLM Agent 默认行为。

**非目标：**

- 不实现 HTTP client。
- 不切换任何 Agent 执行入口。
- 不修改 `agent_task_runs` 表结构。

## Codex 提示词

```text
请执行 P4-E3-S1：新增 apps/api 调用 apps/agents 的配置。
要求使用 TDD；apps/api 只能通过 HTTP 配置指向 apps/agents；不得把 apps/agents 作为本地包 import；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 中现有 LLM Agent 保持不变。
- `apps/agents` 独立服务运行，通过 HTTP API 交互。
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
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agents_settings.py -q
```

结果：`4 failed`，原因是 `Settings` 尚无 `agents_base_url`、`agents_api_key`、`agents_timeout_seconds` 和 `http_agent_runtime_enabled`，符合当前 Story 需要新增配置项的预期。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agents_settings.py -q
```

结果：`4 passed in 0.06s`。

### 实现摘要

- 在 `apps/api/app/settings.py` 的现有配置体系中新增 `agents_base_url`。
- 在 `apps/api/app/settings.py` 的现有配置体系中新增 `agents_api_key`。
- 在 `apps/api/app/settings.py` 的现有配置体系中新增 `agents_timeout_seconds`。
- 支持 `AGENTS_*` 和 `VEHICLE_LEADS_AGENTS_*` 两组环境变量别名。
- 本地默认 `AGENTS_BASE_URL` 为 `http://localhost:8010`。
- 默认 `AGENTS_TIMEOUT_SECONDS` 为 `120`。
- `AGENTS_API_KEY` 为空字符串时会转换为 `None`。
- 新增 `Settings.http_agent_runtime_enabled`，未配置 API Key 时返回 `False`，用于后续 HTTP Agent runtime 显式禁用。
- 新增 `apps/api/.env.example`，只包含安全占位值，不包含真实密钥。
- 更新 `apps/api/README.md`，说明第四阶段 `apps/api` 只能通过 HTTP 配置调用 `apps/agents`，不得把 `apps/agents` 作为本地包导入。
- 未实现 HTTP client。
- 未切换任何 Agent 执行入口。
- 未修改 `agent_task_runs` 表结构。
- 未修改 `apps/api` 现有 LLM Agent 默认行为。

### 验证命令

当前 Story 测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agents_settings.py -q
```

结果：`4 passed in 0.06s`。

`apps/api` 聚焦回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agents_settings.py tests/test_llm_settings.py tests/test_llm_client.py -q
```

结果：`11 passed in 0.09s`。

`apps/api` 导入与默认配置检查：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.main import app
from app.settings import Settings
config = Settings(_env_file=None)
print(app.title)
print(len(app.routes) > 0)
print(config.agents_base_url)
print(config.http_agent_runtime_enabled)
print(config.llm_provider)
PY
```

执行目录：`apps/api`  
结果：

```text
Overseas Vehicle Leads AI API
True
http://localhost:8010
False
deepseek
```

`apps/agents` 回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

执行目录：`apps/agents`  
结果：`49 passed in 0.81s`。

`apps/api` 全量测试尝试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

执行目录：`apps/api`  
结果：`12 failed, 414 passed, 94 errors`。

说明：

- 主要错误为测试夹具连接真实 PostgreSQL/Redis，被当前沙箱网络限制拦截。
- 典型错误：连接 `8.129.17.71:5432` 时 `PermissionError: [Errno 1] Operation not permitted`。
- 该全量失败无法作为本 Story 配置改动的直接回归证据。
- 已用 Story 级测试、LLM 配置/客户端聚焦测试、`apps/api` 导入检查和 `apps/agents` 全量测试完成可用边界内验证。

## 两轮独立评审记录

### 第一轮评审：配置验收、服务边界和文档语言

结论：

- 通过。`apps/api` 可读取 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS`。
- 通过。本地默认地址为 `http://localhost:8010`。
- 通过。未配置 API Key 时，`http_agent_runtime_enabled` 显式为 `False`。
- 通过。未实现 HTTP client，未切换任何 Agent 执行入口。
- 通过。未修改 `agent_task_runs` 表结构。
- 通过。未把 `apps/agents` 作为本地包导入。

发现项：

- 初版 README 新增段落使用英文，不符合“所有过程、结果、注解和文档使用中文”的开发铁律。

修正结果：

- 已将 `apps/api/README.md` 中新增的第四阶段 Agent 配置说明改为中文。

### 第二轮评审：回归风险、安全和可维护性

结论：

- 通过。`Settings` 沿用现有 `apps/api/app/settings.py`，未新建并行配置体系。
- 通过。`agents_api_key` 使用 `SecretStr | None`，避免普通字符串直接暴露。
- 通过。`.env.example` 不包含真实密钥，只包含安全占位值。
- 通过。`apps/api` 聚焦回归通过：`11 passed in 0.09s`。
- 通过。`apps/api` 导入和默认配置检查通过，LLM provider 仍为 `deepseek`。
- 通过。`apps/agents` 回归通过：`49 passed in 0.81s`。

发现项：

- `apps/api` 全量测试在当前沙箱下会尝试连接真实 PostgreSQL/Redis，并因网络权限失败，无法作为本 Story 最终门禁。

修正结果：

- 已记录全量测试失败原因和代表性错误。
- 已补充聚焦回归验证，覆盖本 Story 配置、现有 LLM 设置、LLM client 和应用导入路径。
