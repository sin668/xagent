# E4-S1 生成俄语触达草稿接入执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-4-mobile-workbench/E4-S1-russian-outreach-draft-integration.md`  
Story lock owner：`codex-E4-S1-russian-outreach-draft`

## 执行范围

- 在移动端详情页增加 AI 触达草稿面板。
- 新增触达助手页面，展示俄语草稿、风险提示、话术版本、生成时间、合规检查和 AI 审计。
- 勿扰客户禁用草稿生成入口。
- High/Forbidden 渠道阻断草稿生成和触达动作。
- 人工确认后才允许记录已发送。
- 后端提供读取已生成草稿和记录人工发送接口。

## 主要改动

- `apps/mobile/src/services/outreachDraft.js`
  - 新增草稿 view model、合规检查、禁止承诺检测、勿扰/风险阻断、人工发送记录规则。
- `apps/mobile/src/pages/leads/detail.vue`
  - 新增 AI 触达草稿面板。
- `apps/mobile/src/pages/outreach/index.vue`
  - 新增触达助手页面。
- `apps/mobile/src/data/outreachDraftSeed.js`
  - 新增俄语草稿 seed。
- `apps/mobile/src/styles/outreachDraft.css`
  - 新增触达助手样式。
- `apps/mobile/tests/outreachDraft.test.mjs`
  - 新增移动端合规与人工确认测试。
- `apps/api/app/api/outreach_drafts.py`
  - 新增读取草稿和记录人工发送 API。
- `apps/api/app/services/outreach_draft.py`
  - 新增后端草稿合规与阻断服务。
- `apps/api/app/schemas/outreach_draft.py`
  - 新增后端 schema。
- `apps/api/tests/test_outreach_draft_api.py`
  - 新增后端 API 测试。

## 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| 详情页可展示俄语触达草稿 | 通过 | `pages/leads/detail.vue` |
| 草稿展示风险提示 | 通过 | `riskTips` 页面展示 |
| 勿扰客户不能生成触达草稿 | 通过 | 前后端测试覆盖 |
| High/Forbidden 渠道不能进入触达动作 | 通过 | 前后端测试覆盖 |
| 人工确认后才可记录已发送 | 通过 | `canRecordManualSend` 和后端 API 测试 |
| 后端提供读取已生成草稿接口 | 通过 | `GET /outreach-drafts/{customer_id}` |
| 话术不得承诺最终价格、物流、清关、付款或交付周期 | 通过 | 禁止承诺检测和测试 |
| 每次生成保留 AI 审计记录 | 通过 | 响应包含 `audit`，前后端测试覆盖 |

## 验证命令与结果

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
```

结果：

```text
18 passed
```

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_draft_api.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_channel_risk_api.py
```

结果：

```text
9 passed, 24 warnings
```

```bash
python -m compileall apps/api/app
```

结果：通过。

## 两轮独立评审

### 第一轮评审

结论：发现一个实质缺口，已修正。

发现项：

- 移动端草稿面板和触达助手已实现。
- 合规检查、勿扰阻断、High/Forbidden 阻断、人工确认记录均有移动端测试。
- 缺少 Story 要求的后端草稿接口或读取已生成草稿能力。

修正结果：

- 新增后端读取已生成草稿 API。
- 新增后端人工确认后记录已发送 API。
- 新增后端 schema/service/router/test。
- 真实 PostgreSQL 回归测试通过。

### 第二轮评审

结论：未发现新增实质阻塞问题，E4-S1 可收口。

发现项：

- 勿扰客户、High/Forbidden 渠道均被阻断。
- 草稿不承诺最终价格、物流、清关、付款或交付周期。
- 草稿包含拒绝联系路径。
- AI 审计字段可见。
- 已发送记录必须人工确认，且 `auto_send=false`。
- 当前后端读取固定草稿，符合 Story 二选一要求，但后续需接真实生成与持久化。

修正结果：

- 无新增修正。
- 残留风险已写入 validation。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 后端读取固定草稿 | 满足读取已生成草稿验收 | 后续接 AI 调用、模板库和 AIAuditLog |
| 移动端使用 seed 数据 | 满足当前页面/规则验收 | 后续调用后端 API |
| 未完成 uni-app 真构建/截图 | 当前环境缺少可用移动端依赖安装 | 依赖就绪后补跑构建和截图验证 |
| `datetime.utcnow()` 弃用警告 | 不阻塞当前 Story | 后续统一切换 timezone-aware UTC |

## 下一接力点

Sprint 4 已完成 `E3-S1`、`E3-S2`、`E3-S3`、`E4-S1`。下一步进入 Sprint 5：`E4-S2 触达记录`，需单独获取 Story lock 后继续。
