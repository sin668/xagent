# E5-S2 线索与车源匹配执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-5-business-loop/E5-S2-lead-inventory-matching.md`  
Story lock owner：`codex-E5-S2-matching`

## 执行范围

- 定义轻量匹配规则：车型、年份、价格区间、可出口状态，并复用 E5-S1 报价安全规则。
- 新增 `lead_inventory_matches` 表，记录推荐、推荐理由、风险提示和销售决策。
- 新增推荐接口与决策接口。
- 移动端线索详情页展示推荐车源、推荐理由、价格有效期、可出口状态和合规风险提示。
- 推荐车源明确不等同正式报价；C 级推进报价前必须进入合规复核。

## 主要改动

- `apps/api/app/models/lead_inventory_match.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/schemas/inventory_match.py`
- `apps/api/app/services/inventory_match.py`
- `apps/api/app/api/inventory.py`
- `apps/api/alembic/versions/20260528_0005_add_lead_inventory_matches.py`
- `apps/api/tests/test_inventory_matching_api.py`
- `apps/mobile/src/services/inventoryMatch.js`
- `apps/mobile/src/data/inventoryMatchSeed.js`
- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/src/styles/inventory.css`
- `apps/mobile/tests/inventoryMatch.test.mjs`

## 验收结果

| 验收项 | 结果 |
|---|---|
| 线索详情显示推荐车源 | 通过 |
| 推荐理由字段完整 | 通过 |
| 合规复核风险提示 | 通过 |
| 推进报价/暂不匹配决策 | 通过 |
| 推荐不等同正式报价 | 通过 |
| C 级报价前合规复核 | 通过 |
| 不自动报价 | 通过 |

## 验证结果

```text
alembic upgrade head
通过，已执行 20260528_0004 -> 20260528_0005。
```

```text
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_matching_api.py
2 passed, 18 warnings
```

```text
node --test apps/mobile/tests/inventoryMatch.test.mjs
2 passed
```

```text
PYTHONPATH=apps/api pytest -q apps/api/tests/test_inventory_matching_api.py apps/api/tests/test_inventory_api.py apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py
11 passed, 61 warnings
```

```text
npm --prefix apps/mobile run test
26 passed
```

```text
python -m compileall apps/api/app
node --check apps/mobile/src/services/inventoryMatch.js
node --check apps/mobile/src/data/inventoryMatchSeed.js
通过
```

## 两轮独立评审

### 第一轮评审

结论：发现 Story 主文件未在锁写集中显式声明，已修正。

发现项：

- 推荐接口按轻量规则生成推荐，并过滤不安全车源。
- 移动端详情页已展示推荐理由、有效期、出口状态和风险提示。
- 推荐不等同正式报价的声明已出现。

修正结果：

- 重新获取 Story 锁，补充 Story 主文件到写集。

### 第二轮评审

结论：未发现新增实质阻塞问题，Story 可收口。

发现项：

- `advance_quote` 返回 `formal_quote_allowed=false`。
- C 级线索进入报价前合规复核门禁。
- 未实现自动报价或自动外发。

修正结果：

- 无新增修正。

## 残留风险

- 后续需要接真实 API、鉴权和更细的客户需求结构化提取。
- `datetime.utcnow()` 弃用警告继续作为统一技术债处理。
