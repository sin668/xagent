# E6-S2 勿扰机制执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-3-mvp-data/E6-S2-do-not-contact-mechanism.md`  
Story lock owner：`codex-E6-S2-do-not-contact-mechanism`

## 执行范围

- 实现客户主体级勿扰标记。
- 记录勿扰标记人、时间、原因。
- 实现取消勿扰，并强制记录取消原因。
- 实现触达候选和 AI 话术候选排除勿扰客户。
- 实现触达记录拒绝状态联动客户主体勿扰。
- 补齐飞书同步勿扰状态、原因、标记人和标记时间。

## 主要改动

- `apps/api/app/services/customer_dnc.py`
  - 新增 `CustomerDncService`。
  - 支持 `mark_do_not_contact`、`unmark_do_not_contact`、`list_outreach_candidates`、`list_ai_script_candidates`、`record_outreach_result`。
- `apps/api/app/schemas/customer.py`
  - 新增客户勿扰、候选列表和触达记录 schema。
- `apps/api/app/api/customers.py`
  - 新增客户详情、勿扰标记、取消勿扰、触达候选、AI 话术候选、触达记录 API。
- `apps/api/app/main.py`
  - 挂载 `/customers` router。
- `apps/api/app/services/feishu_mapping.py`
  - `MappedCustomerLead` 增加勿扰标记人和标记时间。
  - 客户线索映射读取 `勿扰标记人`、`勿扰标记时间`。
- `apps/api/app/services/sync_service.py`
  - 飞书同步写入 `do_not_contact_marked_by`、`do_not_contact_marked_at`。
- `apps/api/tests/test_customer_dnc_service.py`
  - 真实 PostgreSQL 服务层测试。
- `apps/api/tests/test_customer_dnc_api.py`
  - 真实 PostgreSQL API 测试。
- `apps/api/tests/test_feishu_sync_service.py`
  - 补充勿扰状态同步不丢失测试。

## API

- `GET /customers/{customer_id}`
- `POST /customers/{customer_id}/do-not-contact`
- `POST /customers/{customer_id}/do-not-contact/cancel`
- `GET /customers/outreach-candidates`
- `GET /customers/ai-script-candidates`
- `POST /customers/{customer_id}/outreach-records`

## 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| 任何用户可在客户详情页标记勿扰 | 通过 | `POST /customers/{customer_id}/do-not-contact` |
| 记录勿扰标记人、时间、原因 | 通过 | 服务/API 测试断言 `do_not_contact_marked_by`、`do_not_contact_marked_at`、`do_not_contact_reason` |
| 勿扰客户不进入触达任务 | 通过 | `list_outreach_candidates` 和 API 测试 |
| AI 生成话术时排除勿扰客户 | 通过 | `list_ai_script_candidates` 和 API 测试 |
| 勿扰状态同步后不丢失 | 通过 | 飞书同步真实 PostgreSQL 测试覆盖状态、原因、标记人、时间 |
| 触达记录“拒绝”状态联动勿扰 | 通过 | 服务/API 测试覆盖 `rejected` 联动 |
| 取消勿扰需要记录原因 | 通过 | 空原因抛错；取消成功记录 `取消勿扰：...` |

## 验证命令与结果

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
nvm use v22.22.0 >/dev/null
PYTHONPATH=apps/api pytest -q apps/api/tests/test_customer_dnc_service.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_feishu_sync_service.py
```

结果：

```text
16 passed, 85 warnings
```

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests
```

结果：

```text
38 passed, 99 warnings
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
print(client.get('/customers/outreach-candidates').status_code)
print(client.get('/customers/ai-script-candidates').status_code)
PY
```

结果：

```text
{'status': 'ok', 'service': 'vehicle-leads-api'}
200
200
```

## 两轮独立评审

### 第一轮评审

结论：发现一个实质缺口，已修正。

发现项：

- 已实现人工标记勿扰、取消勿扰、触达候选排除、AI 话术候选排除和拒绝触达联动。
- 飞书同步勿扰状态验证不完整，仅覆盖状态和原因，未覆盖勿扰标记人/时间。

修正结果：

- 扩展 `MappedCustomerLead` 和飞书映射字段。
- 同步写库时保存 `do_not_contact_marked_by`、`do_not_contact_marked_at`。
- 新增真实 PostgreSQL 测试 `test_customer_sync_preserves_do_not_contact_actor_and_time_from_feishu`。
- 重新运行专项测试，结果 `16 passed`。

### 第二轮评审

结论：未发现新增实质阻塞问题，E6-S2 可收口。

发现项：

- 勿扰客户不会出现在触达候选或 AI 话术候选。
- 取消勿扰必须提供原因。
- 触达记录 `rejected` 会设置客户主体勿扰。
- 飞书同步勿扰状态、原因、标记人、时间不丢失。
- 残留 `datetime.utcnow()` 弃用警告，不影响当前 Story。

修正结果：

- 无新增修正。
- 已在 Story 和 validation 记录技术债。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 不做跨系统全局黑名单同步 | 符合非目标 | 后续如需跨系统同步另开 Story |
| `datetime.utcnow()` 弃用警告 | 不阻塞本 Story | 后续统一切换 timezone-aware UTC 时间 |

## 下一接力点

Prompt 8 / Sprint 3 已完成 `E1-S1`、`E1-S2`、`E6-S1`、`E6-S2`。下一步进入 Sprint 4 移动端工作台第一个 Story：`E3-S1 移动端智能体首页`。

