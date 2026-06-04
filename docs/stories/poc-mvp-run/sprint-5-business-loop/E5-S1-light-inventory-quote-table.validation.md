# E5-S1 维护轻量车源/报价表验收记录

验收日期：2026-05-28  
Story：`docs/stories/sprint-5-business-loop/E5-S1-light-inventory-quote-table.md`  
Story lock owner：`codex-E5-S1-inventory`

## 验收结论

通过。E5-S1 已完成轻量车源/报价数据结构、后端 API、过期与价格确认规则、AI 报价安全阻断、移动端车源匹配页面，并通过 TDD、回归验证和两轮独立评审。

## 验收项

| 验收项 | 结果 | 证据 |
|---|---|---|
| 字段包含品牌、车型、年份、里程、车况、配置、价格、可出口状态、图片/视频、有效期 | 通过 | `InventoryItem`、`InventoryItemCreate`、API 测试 |
| 支持轻量车源录入 | 通过 | `POST /inventory/items` |
| 支持轻量车源查询 | 通过 | `GET /inventory/items` |
| 过期车源有明显提示 | 通过 | `is_expired`、`risk_flags`、移动端 `expiryLabel` |
| 标注价格确认状态 | 通过 | `quote_status`、移动端 `quoteStatusLabel` |
| 未确认价格不能被 AI 当成承诺输出 | 通过 | `can_ai_quote=false`、`blocking_reasons=价格未确认` |
| 过期车源不得推荐为优先报价 | 通过 | `priority_recommendable=false` |
| MVP 不接 ERP/库存系统 | 通过 | 当前仅提供轻量 API 与页面展示 |

## TDD 记录

### RED

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_api.py
```

结果：失败，`/inventory/items` 返回 404。

```bash
node --test apps/mobile/tests/inventory.test.mjs
```

结果：失败，`apps/mobile/src/services/inventory.js` 不存在。

### GREEN

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_api.py
```

结果：`2 passed, 8 warnings`。

```bash
node --test apps/mobile/tests/inventory.test.mjs
```

结果：`2 passed`。

## 回归验证

```bash
alembic upgrade head
```

结果：通过，已执行 `20260528_0003 -> 20260528_0004`。

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py
```

结果：`9 passed, 43 warnings`。

```bash
npm --prefix apps/mobile run test
```

结果：`24 passed`。

```bash
python -m compileall apps/api/app
node --check apps/mobile/src/services/inventory.js
node --check apps/mobile/src/data/inventorySeed.js
```

结果：通过。

## 两轮独立评审

### 第一轮评审

结论：发现一个流程问题并完成修正。

发现项：

- E5-S1 初始锁写集未覆盖 `apps/api/app/main.py` 和 `apps/mobile/src/pages.json`，但实际需要修改后端路由入口和移动端页面配置。
- 后端规则覆盖 Story 要求：未确认价格、过期车源、不可出口和缺少价格均会阻断 AI 报价。
- 移动端页面保留原型中的 hero、筛选 chip、车源列表、有效期和 AI 提示。

修正结果：

- 释放并重新获取 Story 锁，补充 `apps/api/app/main.py`、`apps/mobile/src/pages.json` 和 Story 主文件到写集。

### 第二轮评审

结论：未发现新增实质阻塞问题，E5-S1 可收口。

发现项：

- `can_ai_quote` 和 `priority_recommendable` 使用同一组服务层阻断规则，避免前端绕过。
- 未确认价格不会被 AI 当成承诺输出。
- 过期车源不会进入优先推荐。
- 当前实现没有接 ERP/库存系统，符合非目标。
- 没有自动报价外发行为。

修正结果：

- 无新增修正。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 移动端仍使用 seed 数据 | 规则和页面结构已就绪 | E5-S2 或后续接真实 API 与客户需求匹配 |
| 飞书车源同步尚未接入本 Story | API 已支持录入结构 | 后续复用 E1-S2 同步框架接入车源 Sheet |
| `datetime.utcnow()` 弃用警告 | 不阻塞当前 Story | 后续统一切换 timezone-aware UTC |
