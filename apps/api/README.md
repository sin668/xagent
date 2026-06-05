# Overseas Vehicle Leads AI API

MVP backend data foundation for the overseas vehicle procurement AI lead system.

Current scope:

- FastAPI app skeleton.
- SQLAlchemy model definitions for the Sprint 3 data foundation.
- Alembic initial migration.
- Service-rule helpers for risk blocking, do-not-contact exclusion, and C-grade compliance quote guard.

Runtime stack target:

- Python 3.12+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

## 本地配置

使用 `.env.example` 作为本地配置模板。不要提交真实 API Key。

第四阶段独立 Agent 服务配置：

- `AGENTS_BASE_URL`：默认值为 `http://localhost:8010`。
- `AGENTS_API_KEY`：`apps/api` 调用 `apps/agents` 时使用的内部 API Key。
- `AGENTS_TIMEOUT_SECONDS`：调用 `apps/agents` 的 HTTP 超时时间，默认值为 `120`。

当 `AGENTS_API_KEY` 为空时，`Settings.http_agent_runtime_enabled == False`，HTTP Agent runtime 会被显式禁用。
`apps/api` 只能通过 HTTP 配置调用 `apps/agents`，不得把 `apps/agents` 作为本地包导入。

Local dependency installation is intentionally not vendored in this repository.
