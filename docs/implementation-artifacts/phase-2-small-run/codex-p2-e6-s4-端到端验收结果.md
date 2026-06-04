# P2-E6-S4 真实 PostgreSQL + Redis + LLM + 移动端 H5 端到端验收结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E6-S4-phase2-e2e-verification.md`
- 状态：已完成
- 执行时间：2026-06-03
- 执行范围：仅执行 `P2-E6-S4`
- 锁操作：未执行
- Git 操作：未执行

## 执行环境

```bash
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate booking-room
source /Users/linhuanbin/.reflex/.nvm/nvm.sh
nvm use v22.22.0
```

- Node：`v22.22.0 darwin-arm64`
- npm：`10.9.7`
- Python：`/opt/miniconda3/envs/booking-room/bin/python`
- Python 版本：`3.12.11`

## 服务启动

### API

```bash
/opt/miniconda3/envs/booking-room/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

结果：

```text
Uvicorn running on http://0.0.0.0:8000
```

### 移动端 H5

```bash
npm --prefix apps/mobile run dev:h5
```

结果：

```text
Local: http://localhost:5176/
ready in 1014ms
```

当前运行进程：

- API PID：`64824`
- 移动端 H5 PID：`69673`

## Migration 验证

命令：

```bash
/opt/miniconda3/envs/booking-room/bin/alembic current
/opt/miniconda3/envs/booking-room/bin/alembic upgrade head
/opt/miniconda3/envs/booking-room/bin/alembic current
```

结果：

```text
20260602_0022 (head)
```

结论：通过。

## PostgreSQL 与 Redis 连通性

真实库连通性结果：

```text
postgres_ok=1
public_tables=30
core_counts={
  'llm_prompt_templates': 1,
  'agent_task_runs': 1,
  'lead_source_candidates': 0,
  'staging_leads': 0,
  'customers': 20,
  'ai_audit_logs': 0
}
redis_ping=True
```

结论：PostgreSQL 与 Redis 均通过。

## HTTP 服务验证

### API health

```bash
curl -sS http://127.0.0.1:8000/health
```

结果：

```json
{"status":"ok","service":"vehicle-leads-api"}
```

### LLM health

```bash
curl -sS http://127.0.0.1:8000/llm-health
```

结果：

```json
{
  "provider": "deepseek",
  "models": {
    "default": "deepseek-chat",
    "source_discovery": "deepseek-chat",
    "extraction": "deepseek-chat",
    "grading": "deepseek-chat"
  },
  "base_url_configured": true,
  "api_key_configured": false,
  "configuration_complete": false
}
```

结论：LLM health API 可用，但外部 LLM 真实调用不可用，因为 `api_key_configured=false`。

### 移动端 H5

```bash
curl -sS -I http://127.0.0.1:5176/#/pages/sources/index
```

结果：

```text
HTTP/1.1 200 OK
Content-Type: text/html
```

结论：移动端 H5 服务可访问。

## 端到端验收脚本

新增脚本：

- `apps/api/scripts/phase2_e2e_verification.py`

脚本用途：

- 调用真实 API `/health`、`/llm-health`、`/agent-tasks/source-discovery/run`。
- 在真实 PostgreSQL 中写入 `p2e6s4` 前缀的 Medium、High、Forbidden 来源候选。
- 通过真实 HTTP API 审核 Medium 来源候选，模拟移动端 H5 调用同一接口。
- 使用受控 LLM 输出执行 LEAD_EXTRACTION 写入链路，验证 staging、audit、agent_task_runs。
- 单独核查 High 未审核和 Forbidden 的风险闸门。

语法验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile scripts/phase2_e2e_verification.py
```

结果：通过。

脚本执行命令：

```bash
PYTHONPATH=/Users/linhuanbin/BrianDocs/Workspace/work/yc-work/xagent/apps/api \
/opt/miniconda3/envs/booking-room/bin/python scripts/phase2_e2e_verification.py
```

关键结果：

```json
{
  "postgres_ok": true,
  "redis_checked_by_shell": true,
  "llm_health": {
    "provider": "deepseek",
    "base_url_configured": true,
    "api_key_configured": false,
    "configuration_complete": false
  },
  "source_discovery_run": {
    "status": "failed",
    "created_count": 0
  },
  "mobile_review_response": {
    "risk_level": "Medium",
    "review_status": "approved",
    "approved_for_extraction": true,
    "reviewer_id": "p2e6s4-mobile-reviewer"
  },
  "lead_extraction_selection": {
    "selected_candidate_ids": ["c223bab0-2d26-4a3f-88f1-9ee4023303db"],
    "execution_summary": {
      "processed_count": 1,
      "succeeded_count": 1,
      "failed_count": 0
    }
  },
  "blocked_gate_result": {
    "high": {
      "risk_level": "High",
      "review_status": "high_risk_review",
      "approved_for_extraction": false,
      "block_reason": "high_risk_requires_manual_approval"
    },
    "forbidden": {
      "risk_level": "Forbidden",
      "review_status": "rejected",
      "approved_for_extraction": false,
      "extraction_status": "blocked",
      "block_reason": "forbidden_risk_blocked"
    },
    "forbidden_blocked": true,
    "high_unapproved_blocked": true
  },
  "db_counts_after": {
    "agent_task_runs": 4,
    "lead_source_candidates": 3,
    "staging_leads": 1,
    "ai_audit_logs": 2
  }
}
```

结论：

- SOURCE_DISCOVERY 真实 LLM 任务通过 API 启动并写入审计，但由于 LLM API key 未配置，状态为 `failed`。
- 移动端同源审核 API 可完成来源审核。
- LEAD_EXTRACTION 写入链路可产生 staging 和 AI audit。
- High 未审核与 Forbidden 均未进入自动抽取。

## 移动端验证

### 测试

```bash
npm --prefix apps/mobile test
```

结果：

```text
69 passed
```

### H5 构建

```bash
npm --prefix apps/mobile run build:h5
```

结果：

```text
DONE Build complete.
```

## 验收结论

| 验收项 | 结论 | 说明 |
|---|---|---|
| 真实 PostgreSQL 可查核心表和运行数据 | 通过 | public 表 30 张；验收后写入 `agent_task_runs=4`、`lead_source_candidates=3`、`staging_leads=1`、`ai_audit_logs=2` |
| Redis 可连接 | 通过 | `redis_ping=True` |
| Alembic migration | 通过 | `20260602_0022 (head)` |
| API 服务 | 通过 | `/health` 正常 |
| 移动端 H5 服务 | 通过 | `5176` 返回 `200 OK` |
| LLM health | 部分通过 | API 可用，但 `api_key_configured=false`，真实外部 LLM 调用不可用 |
| SOURCE_DISCOVERY 手动启动 | 部分通过 | 任务可启动并审计；因 API key 未配置失败 |
| 移动端审核来源候选 | 通过 | Medium 来源通过真实 API 审核 |
| LEAD_EXTRACTION 消费审核来源 | 通过 | 使用受控 LLM 输出验证写入链路 |
| staging/core/audit/agent_task_runs 记录 | 部分通过 | staging/audit/agent_task_runs 有新增记录；core 客户表已有数据但本次未新增正式客户 |
| Forbidden 未进入自动抽取 | 通过 | `forbidden_risk_blocked` |
| High 未审核不进入自动抽取 | 通过 | `high_risk_requires_manual_approval` |

## 第一轮独立多维度评审

结论：通过，但必须保留 LLM 未配置事实，不得宣称真实 LLM 调用已成功。

评审维度：

- 真实环境：PostgreSQL、Redis、API、移动端 H5 均使用真实环境。
- 链路完整性：候选来源、人工审核、抽取选择、staging、AI audit、agent_task_runs 均可写入。
- LLM 状态：真实 health 结果明确，未伪造成功。
- 风险边界：Forbidden 与 High 未审核均被阻断。
- 移动端：H5 可访问，测试和构建通过。

发现项与修正结果：

- 发现：`LLM_API_KEY` 未配置，真实 SOURCE_DISCOVERY LLM 调用失败。
- 修正：将该事实记录为验收限制；后续部署文档必须说明如何配置和确认 LLM Agent 正常运行。
- 发现：初版脚本没有覆盖 High/Forbidden 阻断，因为抽取选择器选满后停止扫描。
- 修正：脚本新增 `verify_risk_gate()`，单独核查 High/Forbidden 阻断原因。

## 第二轮独立多维度评审

结论：通过，无新增实质阻塞问题。

复核维度：

- Story 边界：仅完成 `P2-E6-S4`，未执行 `P2-E6-S5`。
- 合规边界：未自动社交私信、未自动加好友、未登录后批量采集、未反爬规避。
- 数据隔离：验收数据使用 `p2e6s4` 前缀，便于识别。
- 审计留痕：失败 SOURCE_DISCOVERY、审核动作、LEAD_EXTRACTION、AI audit 均有记录。
- 残留风险：真实 LLM API key 缺失，需要在部署运行手册中作为必配项和健康检查项。

发现项与修正结果：

- 发现：无新增实质问题。
- 修正：无需修正。

## 后续

下一 Story 可进入 `P2-E6-S5`，重点补充部署运行手册、LLM Agent 启动方式、定时方式和健康确认方式。
