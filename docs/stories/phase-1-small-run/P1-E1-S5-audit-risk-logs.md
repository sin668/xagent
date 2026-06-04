# Story P1-E1-S5：实现 audit/risk 基础日志表

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P1-E1 PostgreSQL 数据底座

## 用户故事

作为合规负责人，我希望 AI 调用、Agent 执行、规则阻断和风险事件都被记录，以便追责和复盘。

## 业务价值

满足 AI 输出可审计、渠道风险可追踪的要求。

## 依赖

- P1-E1-S1

## 实现范围

- 扩展或复用 `ai_audit_logs`。
- 新增 `agent_run_logs`、`review_logs`、`risk_events`。
- 统一记录 task_id、agent_name、action、input_ref、output_ref、result、error_message。

## 数据/API 影响

- 新增日志写入 service。
- 可选新增后台查询 API。

## 验收标准

- LLM 调用必须能记录 prompt_version、model_name、output_json、source_urls。
- 风险事件必须能记录 channel、risk_level、event_type、severity、resolution_status。
- 规则阻断必须记录阻断原因。

## 非目标

- 不做复杂 SIEM 或告警平台。

## 风控检查

- 审计日志不得保存无关私人内容。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/alembic/versions/20260529_0013_audit_risk_logs.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/ai_audit_log.py`
- `apps/api/app/models/agent_run_log.py`
- `apps/api/app/models/review_log.py`
- `apps/api/app/models/risk_event.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/services/audit_risk.py`
- `apps/api/app/services/channel_risk.py`
- `apps/api/tests/test_audit_risk_logs_foundation.py`
- `apps/api/tests/test_integration_postgres_redis.py`
- `_bmad-output/implementation-artifacts/codex-p1-e1-s5-执行结果.md`

### 验收结果

- 复用并扩展 `ai_audit_logs`，新增 `source_urls` 与 `output_json`。
- 新增 `agent_run_logs`、`review_logs`、`risk_events`。
- 统一日志字段覆盖 `task_id`、`agent_name`、`action`、`input_ref`、`output_ref`、`result`、`error_message`。
- LLM 调用可记录 `prompt_version`、`model_name`、`output_json`、`source_urls`。
- 风险事件可记录 `channel`、`risk_level`、`event_type`、`severity`、`resolution_status`。
- 规则阻断会记录 `block_reason`，并在 `ChannelRiskService` 中补充写入 `risk_events`。
- 审计 payload 会移除 `password`、`token`、`secret`、`private_chat` 等无关私人/敏感字段。
- 真实 PostgreSQL migration 因当前工具沙箱网络权限和外部审批服务 503 暂未完成，已在集成测试中将目标版本更新为 `20260529_0013`，待网络通道可用后执行 `alembic upgrade head` 复验。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_audit_risk_logs_foundation.py -q`：5 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0013 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0012:head --sql`：成功生成 PostgreSQL offline SQL，包含 AI 审计扩展字段、`agent_run_logs`、`review_logs`、`risk_events`。

### 风控结果

- 未实现复杂 SIEM 或告警平台。
- 审计日志 service 会移除明显无关私人/敏感字段。
- 规则阻断原因可写入 AI 审计与风险事件。
