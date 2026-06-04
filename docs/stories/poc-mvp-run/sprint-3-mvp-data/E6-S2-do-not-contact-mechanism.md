# Story E6-S2：勿扰机制

## 基本信息

- Epic：E6 合规与风险护栏
- Sprint：Sprint 3 MVP 数据底座
- 优先级：P0
- 状态：Done
- 负责人建议：后端工程 + 客服负责人

## 用户故事

作为客服，我希望客户拒绝后能标记勿扰，以便全渠道停止触达。

## 业务价值

减少投诉、封号和品牌风险。

## 依赖

- E1-S1 定义客户主体模型
- E4-S2 记录触达结果

## 任务清单

- [x] 在客户主体模型增加勿扰状态。
- [x] 记录勿扰标记人、时间、原因。
- [x] 在线索任务查询中排除勿扰客户。
- [x] 在 AI 话术生成任务中排除勿扰客户。
- [x] 同步飞书勿扰状态。
- [x] 为触达记录“拒绝”状态联动勿扰。

## 验收标准

- 任何用户可在客户详情页标记勿扰。
- 勿扰客户不进入触达任务。
- AI 生成话术时排除勿扰客户。
- 勿扰状态同步后不丢失。

## 非目标

- 不做跨系统全局黑名单同步。

## QA / 风控检查

- [x] 勿扰客户不能被任何触达队列查出。
- [x] 取消勿扰需要记录原因。

## 交付记录

完成日期：2026-05-28

### 实现文件

- `apps/api/app/services/customer_dnc.py`：勿扰服务，支持标记/取消勿扰、触达候选查询、AI 话术候选查询、拒绝触达联动勿扰。
- `apps/api/app/schemas/customer.py`：客户勿扰、候选列表和触达记录 API schema。
- `apps/api/app/api/customers.py`：客户勿扰和触达候选 API。
- `apps/api/app/main.py`：挂载 `/customers` 路由。
- `apps/api/app/services/feishu_mapping.py`：飞书客户线索映射新增 `勿扰标记人`、`勿扰标记时间`。
- `apps/api/app/services/sync_service.py`：飞书同步写入 `do_not_contact_marked_by` 和 `do_not_contact_marked_at`。
- `apps/api/tests/test_customer_dnc_service.py`：真实 PostgreSQL 服务层测试。
- `apps/api/tests/test_customer_dnc_api.py`：真实 PostgreSQL API 测试。
- `apps/api/tests/test_feishu_sync_service.py`：补充飞书同步勿扰标记人/时间不丢失测试。

### 后端 API

- `GET /customers/{customer_id}`：查询客户勿扰状态。
- `POST /customers/{customer_id}/do-not-contact`：标记勿扰，记录操作人、时间、原因。
- `POST /customers/{customer_id}/do-not-contact/cancel`：取消勿扰，必须记录原因。
- `GET /customers/outreach-candidates`：触达候选客户，排除勿扰客户。
- `GET /customers/ai-script-candidates`：AI 话术候选客户，排除勿扰客户。
- `POST /customers/{customer_id}/outreach-records`：记录触达结果；`rejected` 或下一步动作 `标记勿扰` 会联动客户主体勿扰。

### 验收命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
nvm use v22.22.0 >/dev/null
PYTHONPATH=apps/api pytest -q apps/api/tests
```

结果：`38 passed, 99 warnings`。警告为 `datetime.utcnow()` 弃用提示，不阻塞本 Story。

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
print(client.get('/customers/outreach-candidates').status_code)
print(client.get('/customers/ai-script-candidates').status_code)
PY
```

结果：健康检查正常，触达候选和 AI 话术候选接口均返回 `200`。

### 两轮评审摘要

- 第一轮：发现飞书同步只保留勿扰状态和原因，未保留勿扰标记人/时间；已补 `勿扰标记人`、`勿扰标记时间` 映射和真实 PostgreSQL 写入测试。
- 第二轮：未发现新增实质阻塞问题；人工标记勿扰、取消勿扰需原因、触达队列排除、AI 话术排除、拒绝触达联动勿扰和飞书同步不丢失均有测试覆盖。

### 残留风险

- `datetime.utcnow()` 弃用警告仍存在，建议后续统一切换为 timezone-aware UTC 时间。
- 本 Story 不做跨系统全局黑名单同步，符合非目标。
