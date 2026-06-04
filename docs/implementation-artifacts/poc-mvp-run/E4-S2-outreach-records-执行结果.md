# E4-S2 触达记录执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-5-business-loop/E4-S2-outreach-records.md`  
Story lock owner：`codex-E4-S2-outreach-records`

## 执行范围

- 新增触达记录创建与历史查询 API。
- 支持已发送、已回复、拒绝、无回复、错误联系方式五类业务状态。
- 支持记录发送人、负责人、下一步动作、结果摘要、话术版本。
- 拒绝联系或下一步为“标记勿扰”时自动联动客户勿扰状态。
- 勿扰客户无法新增触达记录。
- 已发送状态必须由人工确认。
- 移动端触达助手新增人工登记表单，客户详情页新增触达历史。

## 主要改动

- `apps/api/app/models/enums.py`
- `apps/api/app/models/outreach_record.py`
- `apps/api/app/schemas/customer.py`
- `apps/api/app/services/customer_dnc.py`
- `apps/api/app/api/customers.py`
- `apps/api/alembic/versions/20260528_0002_add_outreach_record_statuses.py`
- `apps/api/alembic/versions/20260528_0003_add_outreach_record_owner.py`
- `apps/api/tests/test_outreach_records_api.py`
- `apps/mobile/src/services/outreachRecord.js`
- `apps/mobile/src/data/outreachRecordSeed.js`
- `apps/mobile/src/styles/outreachRecord.css`
- `apps/mobile/src/pages/outreach/index.vue`
- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/tests/outreachRecord.test.mjs`

## 验收结果

| 验收项 | 结果 |
|---|---|
| 触达记录创建 API | 通过 |
| 触达记录历史查询 API | 通过 |
| 五类触达状态 | 通过 |
| 下一步动作和负责人 | 通过 |
| 拒绝后自动勿扰 | 通过 |
| 勿扰客户禁止新增记录 | 通过 |
| 已发送必须人工确认 | 通过 |
| 移动端表单和详情历史 | 通过 |
| 不自动发送 | 通过 |

## 验证结果

```text
alembic upgrade head
通过，已执行 20260528_0002 -> 20260528_0003。
```

```text
PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_outreach_draft_api.py
10 passed, 36 warnings
```

```text
npm --prefix apps/mobile run test
22 passed
```

```text
python -m compileall apps/api/app
通过
```

```text
node --check apps/mobile/src/services/outreachRecord.js
node --check apps/mobile/src/data/outreachRecordSeed.js
通过
```

## 两轮独立评审

### 第一轮评审

结论：发现问题并完成修正。

发现项：

- 负责人字段需要真实落库，不能只复用发送人字段。
- 移动端按钮文案需要匹配当前触达状态。

修正结果：

- 新增 `owner` DB 字段与 migration，API 与测试同步更新。
- 按钮文案改为动态状态文案。

### 第二轮评审

结论：未发现新增实质阻塞问题，Story 可收口。

发现项：

- DNC、人工确认、拒绝转勿扰、状态枚举、历史展示均有测试或代码证据。
- 未发现自动发送或自动社交触达逻辑。

修正结果：

- 无新增修正。

## 残留风险

- 真实 API 接入移动端、管理后台指标可视化、timezone-aware UTC 将在后续 Story 或技术债中处理。
