# E6-S2 Validation：勿扰机制

验证日期：2026-05-28  
Story：`E6-S2 勿扰机制`

## 输入包检查

| 项目 | 结果 | 证据 |
|---|---|---|
| Story ID | 通过 | `docs/stories/sprint-3-mvp-data/E6-S2-do-not-contact-mechanism.md` |
| 用户价值 | 通过 | 客服可在客户拒绝后标记勿扰，全渠道停止触达 |
| 依赖 | 通过 | `E1-S1` 已有客户主体勿扰字段；触达记录模型已有拒绝/触发勿扰字段 |
| 设计对齐 | 通过 | 原型 `lead-detail.html` 有“标记勿扰”动作，`settings.html` 有“勿扰客户自动排除” |
| 强约束 | 通过 | 勿扰客户不得进入触达队列；取消勿扰必须记录原因 |

## 验收映射

| 验收项 | 当前证据 | 结论 |
|---|---|---|
| 任何用户可在客户详情页标记勿扰 | `POST /customers/{customer_id}/do-not-contact`；请求包含 `actor` 与 `reason` | 通过 |
| 记录勿扰标记人、时间、原因 | `CustomerDncService.mark_do_not_contact` 写入 `do_not_contact_marked_by`、`do_not_contact_marked_at`、`do_not_contact_reason` | 通过 |
| 勿扰客户不进入触达任务 | `list_outreach_candidates` 排除 `do_not_contact=True`；服务/API 测试覆盖 | 通过 |
| AI 生成话术时排除勿扰客户 | `list_ai_script_candidates` 复用触达候选排除规则；服务/API 测试覆盖 | 通过 |
| 勿扰状态同步后不丢失 | 飞书映射和同步写入 `是否勿扰`、`勿扰原因`、`勿扰标记人`、`勿扰标记时间`；真实 PostgreSQL 测试覆盖 | 通过 |
| 触达记录“拒绝”状态联动勿扰 | `record_outreach_result` 对 `rejected` 状态设置客户勿扰；服务/API 测试覆盖 | 通过 |
| 勿扰客户不能被任何触达队列查出 | `/customers/outreach-candidates` 和 `/customers/ai-script-candidates` 均排除勿扰客户 | 通过 |
| 取消勿扰需要记录原因 | `unmark_do_not_contact` 空原因抛错；成功取消时记录 `取消勿扰：...` | 通过 |

## 实现文件

- `apps/api/app/services/customer_dnc.py`
- `apps/api/app/schemas/customer.py`
- `apps/api/app/api/customers.py`
- `apps/api/app/main.py`
- `apps/api/app/services/feishu_mapping.py`
- `apps/api/app/services/sync_service.py`
- `apps/api/tests/test_customer_dnc_service.py`
- `apps/api/tests/test_customer_dnc_api.py`
- `apps/api/tests/test_feishu_sync_service.py`

## API 验收

| API | 用途 | 验收 |
|---|---|---|
| `GET /customers/{customer_id}` | 查询客户勿扰状态 | 返回客户主体勿扰字段 |
| `POST /customers/{customer_id}/do-not-contact` | 标记勿扰 | 记录操作人、原因、时间，状态变为 `do_not_contact` |
| `POST /customers/{customer_id}/do-not-contact/cancel` | 取消勿扰 | 必须提供原因，并记录取消原因 |
| `GET /customers/outreach-candidates` | 触达候选 | 排除勿扰客户 |
| `GET /customers/ai-script-candidates` | AI 话术候选 | 排除勿扰客户 |
| `POST /customers/{customer_id}/outreach-records` | 触达记录 | `rejected` 联动客户勿扰 |

## 验证命令

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

## 两轮独立评审记录

### 第一轮评审

结论：发现一个实质验收缺口。

发现项：

- 初始实现和测试已覆盖人工标记勿扰、取消勿扰、触达队列排除、AI 话术排除和拒绝触达联动。
- 但飞书同步只保留 `是否勿扰` 与 `勿扰原因`，未证明 `勿扰标记人` 和 `勿扰标记时间` 不丢失。

修正结果：

- 在 `MappedCustomerLead` 增加 `do_not_contact_marked_by` 与 `do_not_contact_marked_at`。
- 在 `map_customer_lead` 中读取 `勿扰标记人`、`勿扰标记时间`。
- 在 `FeishuSyncService._upsert_customer_lead` 中写入客户主体对应字段。
- 新增 `test_customer_sync_preserves_do_not_contact_actor_and_time_from_feishu`。
- 重新运行相关测试，结果通过。

### 第二轮评审

结论：未发现新增实质阻塞问题。

发现项：

- 服务层和 API 层均覆盖标记/取消勿扰。
- 触达候选和 AI 话术候选均排除勿扰客户。
- 触达记录 `rejected` 状态会联动客户主体勿扰。
- 飞书同步勿扰状态、原因、标记人、时间均可保留。
- 仅剩 `datetime.utcnow()` 弃用警告，不影响当前 Story。

修正结果：

- 无需新增修正。
- 将 `datetime.utcnow()` 记录为后续技术债。

## 残留风险

| 风险 | 影响 | 后续处理 |
|---|---|---|
| 不做跨系统全局黑名单同步 | 符合非目标 | 后续需要跨系统时另开 Story |
| `datetime.utcnow()` 弃用警告 | 长期可能受 Python/SQLAlchemy 行为变化影响 | 后续统一切换为 timezone-aware UTC 时间 |

## 结论

E6-S2 已完成。当前实现满足客户标记勿扰、取消勿扰留痕、触达队列排除、AI 话术排除、飞书同步勿扰状态不丢失、拒绝触达联动勿扰和 QA/风控检查要求。

