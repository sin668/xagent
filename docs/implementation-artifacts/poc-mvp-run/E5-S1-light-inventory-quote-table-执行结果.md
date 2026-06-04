# E5-S1 维护轻量车源/报价表执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-5-business-loop/E5-S1-light-inventory-quote-table.md`  
Story lock owner：`codex-E5-S1-inventory`

## 执行范围

- 扩展 `inventory_items` 数据结构，覆盖配置、图片/视频和有效期。
- 新增轻量车源录入、查询和 AI 报价安全检查 API。
- 新增服务层规则：过期、价格未确认、不可出口、缺少价格均阻断 AI 报价。
- 移动端新增车源匹配页和车源展示服务。
- 通过 TDD 验证未确认价格不得被 AI 当成承诺输出，过期车源不得优先推荐。

## 主要改动

- `apps/api/app/models/inventory_item.py`
- `apps/api/alembic/versions/20260528_0004_extend_inventory_items.py`
- `apps/api/app/schemas/inventory.py`
- `apps/api/app/services/inventory.py`
- `apps/api/app/api/inventory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_inventory_api.py`
- `apps/mobile/src/services/inventory.js`
- `apps/mobile/src/data/inventorySeed.js`
- `apps/mobile/src/styles/inventory.css`
- `apps/mobile/src/pages/inventory/index.vue`
- `apps/mobile/src/pages.json`
- `apps/mobile/tests/inventory.test.mjs`

## 验收结果

| 验收项 | 结果 |
|---|---|
| 车源字段完整 | 通过 |
| 支持录入/查询 | 通过 |
| 过期提示 | 通过 |
| 价格确认状态 | 通过 |
| 未确认价格禁止 AI 承诺 | 通过 |
| 过期车源不优先推荐 | 通过 |
| MVP 不接 ERP | 通过 |

## 验证结果

```text
alembic upgrade head
通过，已执行 20260528_0003 -> 20260528_0004。
```

```text
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_api.py
2 passed, 8 warnings
```

```text
node --test apps/mobile/tests/inventory.test.mjs
2 passed
```

```text
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py
9 passed, 43 warnings
```

```text
npm --prefix apps/mobile run test
24 passed
```

```text
python -m compileall apps/api/app
node --check apps/mobile/src/services/inventory.js
node --check apps/mobile/src/data/inventorySeed.js
通过
```

## 两轮独立评审

### 第一轮评审

结论：发现锁写集覆盖问题并已修正。

发现项：

- `apps/api/app/main.py` 和 `apps/mobile/src/pages.json` 需要纳入 Story 写集。
- 后端服务层已经集中承接 AI 报价安全规则。
- 移动端对齐原型的车源匹配主流程。

修正结果：

- 重新获取 Story 锁并补充写集。

### 第二轮评审

结论：未发现新增实质阻塞问题，Story 可收口。

发现项：

- 未确认价格、过期、不可出口、缺价均无法进入 AI 报价承诺。
- 过期车源不进入优先推荐。
- 无自动外发报价行为。

修正结果：

- 无新增修正。

## 残留风险

- 后续需要接入真实 API 请求、飞书车源同步和 E5-S2 客户需求匹配。
- `datetime.utcnow()` 弃用警告仍作为统一技术债处理。
