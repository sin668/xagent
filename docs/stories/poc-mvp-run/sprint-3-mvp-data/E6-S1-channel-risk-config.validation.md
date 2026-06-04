# E6-S1 Validation：渠道风险等级配置

验证日期：2026-05-28  
Story：`E6-S1 渠道风险等级配置`

## 输入包检查

| 项目 | 结果 | 证据 |
|---|---|---|
| Story ID | 通过 | `docs/stories/sprint-3-mvp-data/E6-S1-channel-risk-config.md` |
| 业务价值 | 通过 | 合规负责人可配置渠道风险等级、允许动作和禁止动作 |
| 依赖 | 通过 | `docs/poc/channel-risk-register.md` 已定义 Low/Medium/High/Forbidden 和渠道 SOP |
| 技术栈 | 通过 | FastAPI、SQLAlchemy、PostgreSQL、真实 Redis 环境沿用 E1-S2 |
| 强约束 | 通过 | High/Forbidden 不能进入自动任务；Forbidden 行为不可执行；阻断记录进入审计日志 |

## 验收映射

| 验收项 | 当前证据 | 结论 |
|---|---|---|
| 支持 Low、Medium、High、Forbidden 四类风险等级 | `ChannelRiskLevel` enum；`ChannelRiskRuleUpsert.risk_level` schema；服务/API 测试覆盖四类 | 通过 |
| High 风险渠道不能被自动任务选择 | `ChannelRiskService.evaluate_ai_task` 调用 `channel_block_reason`；`test_high_risk_rule_blocks_ai_task_and_writes_audit_log` | 通过 |
| Forbidden 行为在系统中不可执行 | Forbidden 风险等级整体阻断；Low 渠道命中 `forbidden_actions` 也阻断；`test_forbidden_rule_blocks_every_action_and_writes_audit_log`、`test_requested_forbidden_action_blocks_even_on_low_risk_channel` | 通过 |
| 每个渠道可记录政策来源链接和备注 | `policy_source_url`、`notes` 字段通过 API 和服务 upsert 保存；`test_upsert_channel_risk_rule_persists_policy_actions_and_notes` | 通过 |
| 风险规则不可只写死在前端 | 规则存储于 PostgreSQL `channel_risk_rules`；后端 `/channel-risks` API 维护和读取 | 通过 |
| 阻断记录应进入审计日志 | `AIAuditLog` 写入 `risk_blocked=True`、`risk_block_reason`；服务/API 测试均验证真实 PostgreSQL 审计落库 | 通过 |
| 在 AI 任务选择前读取风险配置 | `POST /channel-risks/evaluate-ai-task` 从 `channel_risk_rules` 读取规则再返回决策 | 通过 |

## 实现文件

- `apps/api/app/services/channel_risk.py`
- `apps/api/app/schemas/channel_risk.py`
- `apps/api/app/api/channel_risk.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_channel_risk_service.py`
- `apps/api/tests/test_channel_risk_api.py`

## API 验收

| API | 用途 | 验收 |
|---|---|---|
| `GET /channel-risks` | 查询渠道风险规则 | 返回 `200` |
| `PUT /channel-risks/{channel_name}` | 创建/更新规则 | 保存风险等级、允许动作、禁止动作、政策来源、备注 |
| `POST /channel-risks/evaluate-ai-task` | AI 任务前置风险判断 | Low/Medium 放行；High/Forbidden 和命中禁止动作阻断并审计 |

## 验证命令

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

## 两轮独立评审记录

### 第一轮评审

结论：发现一个验收证据补强点。

发现项：

- API 测试已验证 High/Forbidden 返回 `audit_logged=True`，但没有直接查询真实 PostgreSQL 的 `ai_audit_logs` 行数，证据不够强。

修正结果：

- 在 `apps/api/tests/test_channel_risk_api.py` 增加 `count_test_audit_logs()`。
- `test_channel_risk_api_blocks_high_and_forbidden_ai_task_selection` 直接断言真实 PostgreSQL 中新增 2 条测试审计日志。
- 重新运行专项测试，结果 `8 passed`。

### 第二轮评审

结论：未发现新增实质阻塞问题。

发现项：

- 服务层覆盖四类风险等级、High/Forbidden 阻断、Low/Medium 放行、Low 渠道命中禁止动作阻断。
- API 层覆盖规则维护、列表查询、AI 任务评估和阻断审计落库。
- 风险规则在 PostgreSQL 后端读取，不依赖前端硬编码。
- 残留 `datetime.utcnow()` 弃用警告，不影响当前 Story。

修正结果：

- 无需新增修正。
- 将 `datetime.utcnow()` 记录为后续技术债。

## 残留风险

| 风险 | 影响 | 后续处理 |
|---|---|---|
| 不自动判断平台政策变化 | 符合非目标，但需要合规负责人维护规则 | 后续 E8-S2 后台提供更完整的维护界面 |
| `datetime.utcnow()` 弃用警告 | 长期可能受 Python/SQLAlchemy 行为变化影响 | 后续统一切换为 timezone-aware UTC 时间 |

## 结论

E6-S1 已完成。当前实现满足渠道风险等级配置、允许/禁止动作配置、政策来源和备注保存、AI 任务前置风险读取、High/Forbidden 后端阻断和审计日志记录要求。

