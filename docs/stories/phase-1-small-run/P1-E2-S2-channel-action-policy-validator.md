# Story P1-E2-S2：实现渠道允许/禁止动作规则校验

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P1-E2 渠道计划与风险规则

## 用户故事

作为合规负责人，我希望每个 Agent 动作都经过允许/禁止动作校验，以便阻断越界行为。

## 业务价值

把合规边界落到后端规则，而不是只停留在文档。

## 依赖

- P1-E2-S1
- 现有 channel risk rules

## 实现范围

- 新增或扩展 `rule_configs` / `channel_risk_rules`。
- 实现 action validator service。
- 支持 allowed_actions、forbidden_actions、risk_level、source_usage_type 校验。

## 数据/API 影响

- 新增规则查询/校验 API 或 service。

## 验收标准

- login、message、friend_request、join_group、scrape_comments、scrape_followers、bypass_rate_limit 必须被阻断。
- High 渠道只允许 read_public_page、extract_business_contact、capture_limited_evidence 等只读动作。
- 阻断动作必须写 risk_events 或 agent_run_logs。

## 非目标

- 不做自动政策变更监控。

## 风控检查

- 规则必须服务端执行。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/app/services/channel_risk.py`
- `apps/api/app/schemas/channel_risk.py`
- `apps/api/app/api/channel_risk.py`
- `apps/api/tests/test_channel_action_policy_validator.py`
- `docs/stories/phase-1-small-run/P1-E2-S2-channel-action-policy-validator.md`
- `_bmad-output/implementation-artifacts/codex-p1-e2-s2-执行结果.md`

### 验收结果

- 新增服务端 `ChannelActionPolicyValidator`，所有 Agent 动作先经过后端规则判断。
- 全局阻断动作覆盖 `login`、`message`、`friend_request`、`join_group`、`scrape_comments`、`scrape_followers`、`bypass_rate_limit`。
- High 渠道只允许 `read_public_page`、`extract_business_contact`、`capture_limited_evidence`。
- High 渠道必须使用 `public_discovery_only`，否则阻断。
- `allowed_actions`、`forbidden_actions`、`risk_level`、`source_usage_type` 均进入 validator 判断。
- `ChannelRiskService.evaluate_ai_task` 已接入 validator。
- 阻断路径继续调用 `_record_blocked_audit`，写入 AI audit 与 `risk_events`。
- `ChannelRiskEvaluateRequest` 新增 `source_usage_type` 参数。
- 未实现自动政策变更监控。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_action_policy_validator.py -q`：8 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/channel_risk.py apps/api/app/schemas/channel_risk.py apps/api/app/api/channel_risk.py apps/api/tests/test_channel_action_policy_validator.py`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_raw_collection_foundation.py -q`：31 passed。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0014 (head)`。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_risk_service.py -q`：当前工具沙箱网络拦截真实 PostgreSQL，错误为 `PermissionError: [Errno 1] Operation not permitted`；外部网络权限重试被审批服务 503 阻断。

### 风控结果

- 规则由服务端执行，前端或 Agent 请求不能绕过 validator。
- High 渠道保留只读公开动作边界。
- 阻断动作不会静默失败，会进入审计/风险事件写入路径。
