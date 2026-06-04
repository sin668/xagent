# E4-S2 触达记录验收记录

验收日期：2026-05-28  
Story：`docs/stories/sprint-5-business-loop/E4-S2-outreach-records.md`  
Story lock owner：`codex-E4-S2-outreach-records`

## 验收结论

通过。E4-S2 已完成触达记录 API、移动端人工登记表单、客户详情触达历史、拒绝后自动勿扰、DNC 阻断和已发送人工确认规则。

## 验收项

| 验收项 | 结果 | 证据 |
|---|---|---|
| B 级线索可由客服触达并记录结果 | 通过 | `POST /customers/{customer_id}/outreach-records` 与移动端表单 |
| 支持已发送、已回复、拒绝、无回复、错误联系方式 | 通过 | `OutreachStatus`、API schema、移动端状态选项与测试 |
| 支持记录下一步动作和负责人 | 通过 | `next_action` 与 `owner` 字段，`owner` 已通过 migration 落库 |
| 客户拒绝后自动标记勿扰 | 通过 | `rejected` 或 `next_action=标记勿扰` 联动客户 DNC |
| 触达记录可在客户详情页查看 | 通过 | `GET /customers/{customer_id}/outreach-records` 与移动端触达历史 |
| 勿扰客户无法新增触达记录 | 通过 | 后端与移动端测试覆盖 |
| 已发送必须对应人工确认动作 | 通过 | 后端与移动端测试覆盖 |
| 不自动发送 | 通过 | 当前实现仅登记人工触达结果，无自动发送逻辑 |

## 验证命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
cd apps/api
alembic upgrade head
```

结果：通过，已执行 `20260528_0002 -> 20260528_0003`。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_records_api.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_outreach_draft_api.py
```

结果：`10 passed, 36 warnings`。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
```

结果：`22 passed`。

```bash
python -m compileall apps/api/app
node --check apps/mobile/src/services/outreachRecord.js
node --check apps/mobile/src/data/outreachRecordSeed.js
```

结果：通过。

## 两轮独立评审

### 第一轮评审

结论：发现两个实质改进点，均已修正。

发现项：

- `owner` 初版仅通过 `sent_by` 映射返回，不能证明负责人真实落库。
- 移动端触达登记表单可选择多种状态，但按钮文案固定为“记录已发送”，对“已回复/拒绝/无回复/错误联系方式”场景不够准确。

修正结果：

- 新增 `outreach_records.owner` 字段、Alembic migration、service 写入和 API 序列化，并用测试验证 `sent_by` 与 `owner` 不同时仍能保真。
- 移动端按钮文案改为跟随当前状态动态展示，例如“记录已回复”“记录拒绝”。

### 第二轮评审

结论：未发现新增实质阻塞问题，E4-S2 可收口。

发现项：

- 触达状态在后端 schema、枚举、数据库和移动端状态选项中一致。
- DNC 客户无法新增触达记录。
- `sent` 状态必须带人工确认。
- `rejected` 和“标记勿扰”下一步会联动客户勿扰状态。
- 当前实现没有自动发送邮件、社媒私信、自动加好友或登录后批量采集行为。
- 触达历史可作为后续管理后台指标数据源。

修正结果：

- 无新增修正。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 管理后台指标尚未做可视化页面 | 本 Story 已让触达数据进入后端可查询结构 | 后续 Story 中接入管理后台仪表盘 |
| 移动端仍使用 seed 数据展示 | 服务层规则和页面结构已就绪 | 后续接入真实 API 请求与鉴权 |
| `datetime.utcnow()` 弃用警告 | 不阻塞当前 Story | 后续统一切换 timezone-aware UTC |
