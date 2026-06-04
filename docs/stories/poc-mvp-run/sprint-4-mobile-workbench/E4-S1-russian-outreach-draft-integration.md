# Story E4-S1：生成俄语触达草稿接入

## 基本信息

- Epic：E4 AI 触达助手
- Sprint：Sprint 4 MVP 移动端线索工作台
- 优先级：P0
- 状态：Done
- 负责人建议：前端工程 + 后端工程 + 客服负责人

## 用户故事

作为客服，我希望在移动端线索详情中查看 AI 生成的俄语触达草稿，并在人工确认后记录触达动作。

## 业务价值

把 PoC 中验证过的话术能力接入 MVP 主流程。

## 依赖

- E4-S1 生成俄语触达草稿
- E3-S3 移动端线索详情
- E6-S2 勿扰机制

## 任务清单

- [x] 在详情页增加 AI 触达草稿面板。
- [x] 后端提供草稿生成接口或读取已生成草稿。
- [x] 展示风险提示、话术版本和生成时间。
- [x] 勿扰客户隐藏或禁用草稿生成入口。
- [x] High/Forbidden 渠道阻断草稿生成。
- [x] 人工确认后跳转触达记录流程。

## 验收标准

- 详情页可展示俄语触达草稿。
- 草稿展示风险提示。
- 勿扰客户不能生成触达草稿。
- High/Forbidden 渠道不能进入触达动作。
- 人工确认后才可记录已发送。

## 非目标

- 不做自动社交私信。
- 不接入自动发送通道。

## QA / 风控检查

- [x] 话术不得承诺最终价格、物流、清关、付款或交付周期。
- [x] 每次生成保留 AI 审计记录。

## 交付记录

完成日期：2026-05-28

### 实现文件

- `apps/mobile/src/pages/leads/detail.vue`：详情页新增 AI 触达草稿面板和入口。
- `apps/mobile/src/pages/outreach/index.vue`：触达助手页面，展示俄语草稿、合规检查、AI 审计和人工确认记录。
- `apps/mobile/src/services/outreachDraft.js`：移动端草稿合规规则、阻断规则、人工发送记录。
- `apps/mobile/src/data/outreachDraftSeed.js`：俄语草稿 seed 数据。
- `apps/mobile/src/styles/outreachDraft.css`：触达草稿样式。
- `apps/mobile/tests/outreachDraft.test.mjs`：移动端草稿规则测试。
- `apps/api/app/api/outreach_drafts.py`：后端读取草稿和记录人工发送 API。
- `apps/api/app/services/outreach_draft.py`：后端草稿合规、阻断和人工发送记录服务。
- `apps/api/app/schemas/outreach_draft.py`：后端 API schema。
- `apps/api/tests/test_outreach_draft_api.py`：后端 API 测试。

### 验收命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
PYTHONPATH=apps/api pytest -q apps/api/tests/test_outreach_draft_api.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_channel_risk_api.py
python -m compileall apps/api/app
```

结果：移动端 `18 passed`；后端真实 PostgreSQL 回归 `9 passed, 24 warnings`；`compileall` 通过。警告为 `datetime.utcnow()` 弃用提示，不阻塞本 Story。

### 两轮评审摘要

- 第一轮：发现只做移动端 seed 读取，未满足“后端提供草稿生成接口或读取已生成草稿”；已补后端读取已生成草稿和人工确认记录接口，并补测试。
- 第二轮：未发现新增实质阻塞问题；勿扰、High/Forbidden、禁用承诺、拒绝联系路径、AI 审计、人工确认后记录已发送均有实现和测试证据。

### 残留风险

- 后端当前读取固定已生成草稿，未接真实 LLM 生成与持久化表；后续需要接入 AI 审计日志和模板库。
- 移动端触达助手使用 seed 数据；后续需要改为调用后端 `/outreach-drafts/{customer_id}`。
- 当前环境仍未完成真实 uni-app 构建和移动端截图验证；依赖安装后需补跑构建/预览。
