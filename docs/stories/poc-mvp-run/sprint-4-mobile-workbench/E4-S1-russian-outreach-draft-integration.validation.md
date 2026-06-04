# E4-S1 Validation：生成俄语触达草稿接入

验证日期：2026-05-28  
Story：`E4-S1 生成俄语触达草稿接入`

## 输入包检查

| 项目 | 结果 | 证据 |
|---|---|---|
| Story ID | 通过 | `docs/stories/sprint-4-mobile-workbench/E4-S1-russian-outreach-draft-integration.md` |
| 用户价值 | 通过 | 客服可在移动端查看 AI 俄语草稿，并人工确认后记录触达 |
| 依赖 | 通过 | E3-S3 详情页、E6-S2 勿扰机制、FAQ/俄语模板 |
| 原型对齐 | 通过 | 参考 `prototypes/mvp-mobile-agent/pages/outreach.html` |
| 强约束 | 通过 | 不自动社交私信，不接自动发送通道，High/Forbidden 阻断，勿扰阻断 |

## 验收映射

| 验收项 | 当前证据 | 结论 |
|---|---|---|
| 详情页可展示俄语触达草稿 | `pages/leads/detail.vue` 新增 AI 触达草稿面板 | 通过 |
| 草稿展示风险提示 | `outreachDraftSeed.riskTips` 和触达助手页面展示 | 通过 |
| 勿扰客户不能生成触达草稿 | `buildOutreachDraftViewModel` 阻断 `doNotContact`；测试覆盖 | 通过 |
| High/Forbidden 渠道不能进入触达动作 | 移动端与后端均阻断 High/Forbidden；测试覆盖 | 通过 |
| 人工确认后才可记录已发送 | `canRecordManualSend` 与后端 `/record-manual-send` 均要求 `human_confirmed=true` | 通过 |
| 后端提供草稿生成接口或读取已生成草稿 | `GET /outreach-drafts/{customer_id}` 返回已生成草稿 | 通过 |

## QA / 风控检查

| 检查项 | 证据 | 结论 |
|---|---|---|
| 话术不得承诺最终价格、物流、清关、付款或交付周期 | `hasForbiddenCommitments` 和后端 `has_forbidden_commitments` 检查；测试覆盖风险文本 | 通过 |
| 每次生成保留 AI 审计记录 | 草稿响应包含 `audit.model/prompt_version/input_saved/output_saved`；前后端测试覆盖 | 通过 |
| 模板必须可外发 | 合规检查 `template_approved` 要求 `templateStatus/template_status=可外发` | 通过 |
| 包含拒绝联系路径 | 合规检查 `has_refusal_path`；测试覆盖 | 通过 |
| 不接自动发送通道 | 前端/后端响应均 `autoSendEnabled/auto_send_enabled=false`；记录结果 `auto_send=false` | 通过 |

## 实现文件

- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/src/pages/outreach/index.vue`
- `apps/mobile/src/pages.json`
- `apps/mobile/src/styles/outreachDraft.css`
- `apps/mobile/src/data/outreachDraftSeed.js`
- `apps/mobile/src/services/outreachDraft.js`
- `apps/mobile/tests/outreachDraft.test.mjs`
- `apps/api/app/api/outreach_drafts.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas/outreach_draft.py`
- `apps/api/app/services/outreach_draft.py`
- `apps/api/tests/test_outreach_draft_api.py`

## 验证命令

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

说明：首次非提升权限运行真实 PostgreSQL 回归时因沙箱网络权限报 `Operation not permitted`，按项目真实 DB 验证要求提升权限重跑后通过。

```bash
python -m compileall apps/api/app
```

结果：通过。

## 两轮独立评审记录

### 第一轮评审

结论：发现一个实质缺口，已修正。

发现项：

- 移动端已实现详情页草稿面板、触达助手页面、合规检查、勿扰阻断、High/Forbidden 阻断和人工确认记录。
- 移动端规则测试已覆盖禁止承诺、拒绝联系路径、AI 审计和自动发送关闭。
- 但 Story 明确要求“后端提供草稿生成接口或读取已生成草稿”，初始实现仅使用移动端 seed，缺少后端接口。

修正结果：

- 新增 `GET /outreach-drafts/{customer_id}` 读取已生成草稿。
- 新增 `POST /outreach-drafts/{customer_id}/record-manual-send`，仅在人工确认且合规检查通过后记录人工发送。
- 新增后端 schema、service、router 和 API 测试。
- 真实 PostgreSQL 回归测试通过。

### 第二轮评审

结论：未发现新增实质阻塞问题。

发现项：

- 勿扰客户不能生成草稿或记录发送。
- High/Forbidden 风险渠道不能生成草稿或进入触达动作。
- 草稿包含拒绝联系路径。
- 草稿不允许包含最终价格、物流、清关、付款、交付周期承诺。
- 只有人工确认后才能记录已发送，且 `auto_send=false`。
- 后端当前为读取已生成草稿，未接真实 LLM 生成，符合 Story 二选一口径但需后续产品化。

修正结果：

- 无新增代码修正。
- 将真实 LLM/模板库/审计持久化、移动端 API 接入和构建验证列为残留风险。

## 残留风险

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 后端读取固定草稿 | 满足“读取已生成草稿”验收 | 后续接入模板库、AI 调用和 AIAuditLog 持久化 |
| 移动端仍使用 seed 草稿 | 满足当前页面和规则验收 | 后续改为调用 `/outreach-drafts/{customer_id}` |
| 未完成真实 uni-app 构建/截图 | 当前环境缺少可用移动端依赖安装 | 依赖就绪后补跑 uni-app dev/build 与移动端截图验证 |
| `datetime.utcnow()` 弃用警告 | 不阻塞当前 Story | 后续统一切换 timezone-aware UTC |

## 结论

E4-S1 已完成。当前实现满足详情页草稿展示、触达助手、风险提示、后端读取已生成草稿、勿扰阻断、High/Forbidden 阻断、人工确认记录和 AI 审计要求。
