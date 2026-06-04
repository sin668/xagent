# E5-S2 线索与车源匹配验收记录

验收日期：2026-05-28  
Story：`docs/stories/sprint-5-business-loop/E5-S2-lead-inventory-matching.md`  
Story lock owner：`codex-E5-S2-matching`

## 验收结论

通过。E5-S2 已完成轻量匹配规则、后端推荐/决策接口、移动端线索详情推荐展示、风险提示和报价前合规门禁。

## 验收项

| 验收项 | 结果 | 证据 |
|---|---|---|
| 线索详情可显示推荐车源 | 通过 | `apps/mobile/src/pages/leads/detail.vue` |
| 推荐理由包含车型、年份、车况、价格有效期和可出口状态 | 通过 | `InventoryMatchService._build_reason` 与后端测试 |
| 需要合规复核的车源有风险提示 | 通过 | C 级或请求指定合规复核时返回风险提示 |
| 支持销售选择“推进报价”或“暂不匹配” | 通过 | `POST /inventory/matches/{match_id}/decision` |
| 推荐车源不得等同于正式报价 | 通过 | `quote_disclaimer` 与 `formal_quote_allowed=false` |
| C 级报价前必须走合规复核 | 通过 | `next_gate= C级线索报价前必须完成合规复核` |
| 不做自动报价 | 通过 | 当前仅记录推荐与销售决策，无报价生成/外发 |
| 不做复杂推荐算法 | 通过 | 仅使用车型、年份、价格区间、可出口和报价安全规则 |

## TDD 记录

### RED

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_matching_api.py
```

结果：失败，`LeadInventoryMatch` 模型不存在。

```bash
node --test apps/mobile/tests/inventoryMatch.test.mjs
```

结果：失败，`apps/mobile/src/services/inventoryMatch.js` 不存在。

### GREEN

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_matching_api.py
```

结果：`2 passed, 18 warnings`。

```bash
node --test apps/mobile/tests/inventoryMatch.test.mjs
```

结果：`2 passed`。

## 回归验证

```bash
alembic upgrade head
```

结果：通过，已执行 `20260528_0004 -> 20260528_0005`。

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_matching_api.py apps/api/tests/test_inventory_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py
```

结果：`11 passed, 61 warnings`。

```bash
npm --prefix apps/mobile run test
```

结果：`26 passed`。

```bash
python -m compileall apps/api/app
node --check apps/mobile/src/services/inventoryMatch.js
node --check apps/mobile/src/data/inventoryMatchSeed.js
```

结果：通过。

## 两轮独立评审

### 第一轮评审

结论：发现一个流程覆盖问题并完成修正。

发现项：

- 需要回写 Story 主文件，但初始锁写集中未显式包含 `docs/stories/sprint-5-business-loop/E5-S2-lead-inventory-matching.md`。
- 后端推荐接口已过滤掉未通过 E5-S1 AI 报价安全规则的车源。
- 推荐说明包含“不等同正式报价”声明。
- 移动端详情页展示推荐理由、有效期、出口状态和合规提示。

修正结果：

- 释放并重新获取 Story 锁，补充 Story 主文件、validation 和执行结果到写集。

### 第二轮评审

结论：未发现新增实质阻塞问题，E5-S2 可收口。

发现项：

- 轻量匹配规则符合非目标，没有引入复杂推荐算法。
- `advance_quote` 只进入报价前合规复核门禁，`formal_quote_allowed=false`。
- C 级线索报价前合规复核提示在后端响应和移动端展示中均可见。
- 当前无自动报价、自动外发或承诺最终价格行为。

修正结果：

- 无新增修正。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 移动端仍使用 seed 匹配数据 | 页面与规则已就绪 | 后续接真实 API 与鉴权 |
| 匹配请求来自轻量条件，不解析客户自然语言需求 | 符合“不做复杂推荐算法”非目标 | 后续可在新 Story 中接 AI 需求抽取 |
| `datetime.utcnow()` 弃用警告 | 不阻塞当前 Story | 后续统一切换 timezone-aware UTC |
