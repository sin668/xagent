# Vehicle Leads Agents

第四阶段独立 Agent 服务，用于小范围运行 LangGraph Agent 迁移。

## 定位

- 作为独立 FastAPI 服务运行，默认监听 `127.0.0.1:8010` 或内网地址。
- `apps/api` 继续作为业务入口，默认监听 `127.0.0.1:8000`。
- `apps/api` 通过 HTTP API 调用 `apps/agents`，不把 `apps/agents` 作为本地 Python 包注入。
- Deep Enrichment 和 Lead Cleanup 可在第四阶段受控 active_run。
- Source Discovery 和 Lead Extraction/Grading 在第四阶段只做 shadow_run。
- LangGraph 负责 Agent 内部的多步骤流程表达、分支、状态流转、重试和审计摘要。

## 数据与合规边界

- Agent 服务不得直接写 `customers`、`lead_sources`、`contact_methods`、`staging_leads` 等 core 表。
- Agent 服务只写自己的运行状态表，例如后续 Story 中的 `agent_service_runs`。
- Agent 服务只输出结构化候选结果、shadow 对照结果和审计摘要。
- 所有业务表写入、schema 校验、风险硬门禁、人工确认、客户晋级、字段采纳和清洗执行必须交由 `apps/api` 负责。
- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- 不自动晋级客户。
- 不自动归并客户。
- 不自动恢复 Invalid。
- 不自动触达客户。

## 第四阶段本地启动

第四阶段本地小范围运行不要求 Docker Compose。默认使用两个独立进程：

| 服务 | 默认端口 | 启动目录 | 说明 |
|---|---:|---|---|
| `apps/api` | `8000` | `apps/api` | 业务入口、权限、人工审核、业务表写入 |
| `apps/agents` | `8010` | `apps/agents` | LangGraph Agent API、运行状态、重试和审计摘要 |

### apps/api

```bash
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

第四阶段调用 `apps/agents` 时，`apps/api` 需要配置：

```bash
AGENTS_BASE_URL=http://127.0.0.1:8010
AGENTS_API_KEY=change_me_for_local_only
AGENTS_TIMEOUT_SECONDS=120
```

### apps/agents

```bash
cd apps/agents
AGENTS_API_KEY=change_me_for_local_only \
AGENTS_DATABASE_URL=sqlite:///./agents.db \
uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

健康检查：

```bash
curl http://127.0.0.1:8010/health
```

OpenAPI 文档：

```text
http://127.0.0.1:8010/docs
```

### LangGraph Studio 可视化

`apps/agents` 提供 `langgraph.json`，用于在 LangGraph Studio 中查看第四阶段 Agent 图：

- `deep_enrichment`
- `lead_cleanup`
- `source_discovery`
- `lead_extraction_grading`

本地启动：

```bash
cd apps/agents
python -m pip install -e ".[studio]"
langgraph dev
```

Studio 会读取 `langgraph.json` 中的 `app.studio.graphs:*` 导出。`lead_extraction_grading` 使用 Studio 专用组合视图展示抽取、分级和组合校验三个阶段；实际 HTTP API 仍使用 `LeadExtractionGradingGraphRunner` 运行。

### 运行日志

Agent API 和 LangGraph 节点运行会通过 `app.agent_run` logger 打印结构化文本日志，覆盖：

- `agent_run_start`：Agent run 创建并进入 running。
- `agent_node_start` / `agent_node_finish`：每个 LangGraph 节点进入和完成。
- `agent_node_failed`：节点异常。
- `agent_run_succeeded` / `agent_run_failed`：Agent run 最终结果。

### 内部 API Key

- 受保护的 Agent Run API 使用 Header：`X-Agents-Api-Key: <AGENTS_API_KEY>`。
- `apps/api` 和 `apps/agents` 必须使用同一组 `AGENTS_API_KEY`。
- `/health` 保持公开，用于本机健康检查。
- 第四阶段不实现用户级 JWT、RBAC 或外部身份系统；用户权限仍由 `apps/api` 控制。

### Agent 运行状态数据库

- `apps/agents` 使用 `AGENTS_DATABASE_URL` 连接自己的 Agent 运行状态库。
- 未配置 `AGENTS_DATABASE_URL` 时，会回退读取 `DATABASE_URL`。
- 本地小范围运行默认值为 `sqlite:///./agents.db`。
- `apps/agents` 只写 `agent_service_runs` 等自身运行状态表，不直接写 `customers`、`contact_methods`、`staging_leads` 等业务 core 表。

## 运行边界

- 不要把 `apps/agents` 暴露到公网。
- 不要让前端或外部客户端直接调用 `apps/agents`。
- 不要通过本地包 import 方式让 `apps/api` 调用 `apps/agents`。
- Docker Compose 不是第四阶段本地小范围运行的必需项；如后续需要容器化，应作为单独部署 Story 或运维任务处理。
