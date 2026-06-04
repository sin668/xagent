# E6-S1 渠道风险等级配置执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-3-mvp-data/E6-S1-channel-risk-config.md`  
Story lock owner：`codex-E6-S1-channel-risk-config`

## 执行范围

- 实现后端渠道风险规则维护能力。
- 实现 AI/Agent 任务选择前置风险评估。
- 对 High/Forbidden 渠道返回阻断原因。
- 对命中渠道禁止动作的请求返回阻断原因。
- 将阻断记录写入 `ai_audit_logs`，保留输入、输出、来源链接、模型名、prompt 版本和阻断原因。

## 主要改动

- `apps/api/app/services/channel_risk.py`
  - 新增 `ChannelRiskService`。
  - 支持 `upsert_rule`、`list_rules`、`evaluate_ai_task`。
  - Low/Medium 默认允许 AI 处理；High/Forbidden 阻断；Low/Medium 命中 `forbidden_actions` 也阻断。
  - 阻断时写入 `AIAuditLog(risk_blocked=True)`。
- `apps/api/app/schemas/channel_risk.py`
  - 新增渠道风险配置、列表和任务评估 schema。
- `apps/api/app/api/channel_risk.py`
  - 新增 `GET /channel-risks`。
  - 新增 `PUT /channel-risks/{channel_name}`。
  - 新增 `POST /channel-risks/evaluate-ai-task`。
- `apps/api/app/main.py`
  - 挂载渠道风险 API router。
- `apps/api/tests/test_channel_risk_service.py`
  - 使用真实 PostgreSQL 验证服务层规则。
- `apps/api/tests/test_channel_risk_api.py`
  - 使用真实 PostgreSQL 验证 API 和审计落库。

## 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| 支持 Low、Medium、High、Forbidden 四类风险等级 | 通过 | schema enum pattern、模型 enum、服务/API 测试 |
| High 风险渠道不能被自动任务选择 | 通过 | `test_high_risk_rule_blocks_ai_task_and_writes_audit_log` |
| Forbidden 行为在系统中不可执行 | 通过 | `test_forbidden_rule_blocks_every_action_and_writes_audit_log`、`test_requested_forbidden_action_blocks_even_on_low_risk_channel` |
| 每个渠道可记录政策来源链接和备注 | 通过 | `test_upsert_channel_risk_rule_persists_policy_actions_and_notes` |
| 风险规则不可只写死在前端 | 通过 | 后端 API + PostgreSQL `channel_risk_rules` |
| 阻断记录进入审计日志 | 通过 | 服务/API 均直接断言 `ai_audit_logs` 真实落库 |

## 验证命令与结果

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
nvm use v22.22.0 >/dev/null
PYTHONPATH=apps/api pytest -q apps/api/tests/test_channel_risk_service.py apps/api/tests/test_channel_risk_api.py
```

结果：

```text
8 passed, 14 warnings
```

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests
```

结果：

```text
30 passed, 53 warnings
```

```bash
python -m compileall apps/api
```

结果：通过。

```bash
PYTHONPATH=apps/api python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
print(client.get('/health').json())
print(client.get('/channel-risks').status_code)
PY
```

结果：

```text
{'status': 'ok', 'service': 'vehicle-leads-api'}
200
```

## 两轮独立评审

### 第一轮评审

结论：发现 API 审计验收证据不足。

发现项：

- API 测试只验证响应中的 `audit_logged=True`，未直接证明 `ai_audit_logs` 已真实写入 PostgreSQL。

修正结果：

- 在 `apps/api/tests/test_channel_risk_api.py` 增加真实 PostgreSQL 审计日志数量查询。
- High 和 Forbidden 两次 API 阻断后断言新增 2 条 `model_name=test-risk-api` 的审计日志。
- 重新运行专项测试，结果 `8 passed`。

### 第二轮评审

结论：未发现新增实质阻塞问题，E6-S1 可收口。

发现项：

- 服务层和 API 层均覆盖 High/Forbidden 阻断。
- Forbidden 动作即使发生在 Low 渠道，也会被后端阻断并审计。
- Low/Medium 未命中禁止动作时允许进入 AI 任务候选。
- 政策来源链接和备注已保存到后端数据库。
- 风险规则由后端读取，不依赖前端硬编码。
- 仅存在 `datetime.utcnow()` 弃用警告，属于后续统一技术债。

修正结果：

- 无新增修正。
- 已在 Story 和 validation 中记录残留风险。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 平台政策变化不自动识别 | 符合 Story 非目标；规则由合规负责人维护 | 后续 E8-S2 管理后台提供维护界面 |
| `datetime.utcnow()` 弃用警告 | 不阻塞本 Story | 后续统一切换 timezone-aware UTC 时间 |

## 下一接力点

Prompt 8 的下一个 Story：`E6-S2 勿扰机制`。

