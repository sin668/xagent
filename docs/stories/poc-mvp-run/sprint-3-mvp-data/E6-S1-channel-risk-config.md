# Story E6-S1：渠道风险等级配置

## 基本信息

- Epic：E6 合规与风险护栏
- Sprint：Sprint 3 MVP 数据底座
- 优先级：P0
- 状态：Done
- 负责人建议：后端工程 + 合规/风控

## 用户故事

作为合规负责人，我希望配置每个渠道的风险等级、允许动作和禁止动作。

## 业务价值

确保 AI/Agent 和人工操作都在边界内。

## 依赖

- E0-S2 创建 PoC 渠道风险登记表

## 任务清单

- [x] 设计渠道风险配置表。
- [x] 支持 Low、Medium、High、Forbidden 风险等级。
- [x] 支持允许动作和禁止动作配置。
- [x] 保存政策来源链接和备注。
- [x] 在 AI 任务选择前读取风险配置。
- [x] 对 High/Forbidden 渠道返回阻断原因。

## 验收标准

- 支持 Low、Medium、High、Forbidden 四类风险等级。
- High 风险渠道不能被自动任务选择。
- Forbidden 行为在系统中不可执行。
- 每个渠道可记录政策来源链接和备注。

## 非目标

- 不自动判断所有平台最新政策变化。

## QA / 风控检查

- [x] 风险规则不可只写死在前端。
- [x] 阻断记录应进入审计日志。

## 交付记录

完成日期：2026-05-28

### 实现文件

- `apps/api/app/services/channel_risk.py`：渠道风险配置服务，支持规则 upsert、规则列表、AI 任务前置风险判断和阻断审计。
- `apps/api/app/schemas/channel_risk.py`：渠道风险配置与 AI 任务判断 API schema。
- `apps/api/app/api/channel_risk.py`：渠道风险配置后端 API，提供规则维护、列表查询和 AI 任务选择前评估入口。
- `apps/api/app/main.py`：挂载 `/channel-risks` 路由。
- `apps/api/tests/test_channel_risk_service.py`：真实 PostgreSQL 服务层测试，覆盖四级风险、允许/禁止动作、High/Forbidden 阻断和审计日志。
- `apps/api/tests/test_channel_risk_api.py`：真实 PostgreSQL API 测试，覆盖规则维护、列表、AI 任务评估和审计落库。

### 后端 API

- `GET /channel-risks`：列出渠道风险规则。
- `PUT /channel-risks/{channel_name}`：创建或更新渠道风险规则。
- `POST /channel-risks/evaluate-ai-task`：AI/Agent 任务选择前读取渠道规则；Low/Medium 且未命中禁止动作时允许；High/Forbidden 或命中禁止动作时阻断并写入 `ai_audit_logs`。

### 验收命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
nvm use v22.22.0 >/dev/null
PYTHONPATH=apps/api pytest -q apps/api/tests
```

结果：`30 passed, 53 warnings`。警告为 `datetime.utcnow()` 弃用提示，不阻塞本 Story。

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

结果：健康检查正常，`GET /channel-risks` 返回 `200`。

### 两轮评审摘要

- 第一轮：发现 API 层仅验证 `audit_logged=True`，缺少直接证明 `ai_audit_logs` 真实落库的断言；已补充 API 测试中的真实 PostgreSQL 审计日志数量断言。
- 第二轮：未发现新增实质阻塞问题；High/Forbidden 后端阻断、Forbidden 动作阻断、Low/Medium 放行、政策来源和备注保存均已有测试覆盖。

### 残留风险

- `datetime.utcnow()` 弃用警告仍存在，建议后续统一切换为 timezone-aware UTC 时间。
- 本 Story 不自动判断平台最新政策变化；政策更新仍依赖合规负责人维护渠道规则。
