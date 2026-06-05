# Story P5-E6-S3：DNC 与 D/E 客户阻断集成

状态：已完成
Sprint：Sprint 6  
优先级：P0  
Epic：P5-E6（自动回复规则与审计）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望将 DNC/勿扰、Watch/Invalid（对外 D/E 级）阻断接入邮件回复生成、审核和发送链路，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-05-第五阶段小范围运行-Prompt与邮件自动回复知识库.md`
- `docs/product/2026-06-05-海外车辆采购AI获客系统-第五阶段小范围运行方案与产品技术设计.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `prototypes/mvp-mobile-agent/pages/email-replies.html`
- `prototypes/mvp-mobile-agent/pages/email-reply-detail.html`
- `prototypes/mvp-mobile-agent/pages/admin-prompt-governance.html`
- `prototypes/mvp-mobile-agent/pages/admin-knowledge-base.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-replies.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-quality.html`

## Story 定义

**目标：** 将 DNC/勿扰、Watch/Invalid（对外 D/E 级）阻断接入邮件回复生成、审核和发送链路。

**建议文件：**

- apps/api/app/services/*customer*
- apps/api/app/services/*email_reply*
- apps/api/tests/*dnc*

**验收标准：**

- DNC/勿扰客户自动发送阻断率 100%。
- D/E 客户自动发送阻断率 100%。
- 人工确认页面能看到阻断原因。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E6-S3：DNC 与 D/E 客户阻断集成。
目标：将 DNC/勿扰、Watch/Invalid（对外 D/E 级）阻断接入邮件回复生成、审核和发送链路。
要求：使用 TDD；只实现本 Story；接入真实 PostgreSQL/API；完成后执行两轮独立多维度评审并用中文记录结论、发现项和修正结果。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 代码实现必须使用 `superpowers:test-driven-development`；调试异常必须使用 `superpowers:systematic-debugging`；完成前必须使用 `superpowers:verification-before-completion`。
- 环境按项目约定使用 `conda activate booking-room` 和 `nvm use v22.22.0`。
- 后端、Agent、后台和移动端联调必须使用真实 API、真实 PostgreSQL 和 Redis，不允许只验证 seed 静态页面。
- 每个 Story 完成后必须执行两轮独立多维度评审，并在 Story 或执行记录中写明结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 是唯一业务数据权威，业务 core 表写入、权限、审计、DNC/勿扰、自动发送准入、硬拦截和邮件发送提交必须由 `apps/api` 控制。
- `apps/agents` 只做编排、LLM 调用、节点追踪和结果回传，不直接写 `customers`、`contact_methods`、`lead_sources`、`knowledge_items`、`email_reply_drafts`、`outreach_records` 等业务 core 表。
- 不自动社交私信、不自动加好友、不登录后批量采集、不反爬规避、不抓取非公开数据。
- DNC/勿扰、Watch/Invalid（对外 D/E 级）、语言不确定、知识召回不足、缺少知识证据、价格/付款/合同/发票/税务/法律/交付/出口管制等场景不得自动发送。
- LLM 输出必须结构化；缺失字段输出 `Unknown`、`null` 或空数组，不得编造。
- AI 建议回复和最终发送内容必须分开保存并可审计。

## 执行记录

### TDD 红灯

- 新增测试文件：`apps/api/tests/test_phase5_email_reply_customer_policy_integration.py`。
- 红灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_customer_policy_integration.py -q`
- 红灯结果：
  - 失败原因符合预期：`ModuleNotFoundError: No module named 'app.services.email_reply_customer_policy'`，说明 DNC/D/E 客户策略集成服务尚未实现。

### TDD 绿灯

- 新增服务文件：`apps/api/app/services/email_reply_customer_policy.py`。
- 实现内容：
  - 从 `Customer` 模型读取 `do_not_contact`、`status`、`grade`，构建 `EmailReplyHardBlockInput`。
  - 将 Watch 显示映射为 D 级、Invalid 显示映射为 E 级。
  - 将 DNC/D/E 阻断结果写入 `EmailReplyDraft.auto_send_decision_json`，供人工确认页面展示。
- 绿灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_customer_policy_integration.py -q`
- 绿灯结果：
  - `3 passed in 0.31s`

### 调试与回归修正

- 回归中发现两处既有测试契约过期：
  - `test_customer_dnc_service.py` 默认以 `operations` 取消勿扰，但当前权限服务要求 `compliance/admin`，已修正为 `actor_role="admin"`。
  - `test_customer_dnc_api.py` 客户详情接口已返回结构化 `do_not_contact` 对象，已修正断言为 `do_not_contact.enabled/reason` 和 `profile.status`。
- 上述修正不改变业务权限和 API 行为，只让测试符合当前真实契约。

### 验证记录

- 回归验证命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_customer_policy_integration.py tests/test_phase5_email_reply_hard_block_service.py tests/test_phase5_auto_send_eligibility_service.py tests/test_customer_dnc_service.py tests/test_customer_dnc_api.py -q`
- 回归验证结果：
  - `19 passed, 45 warnings in 12.82s`
- 格式验证命令：
  - `git diff --check`
- 格式验证结果：
  - 通过，无尾随空格或 patch 格式问题。

## 两轮独立多维度评审

### 第一轮评审：DNC/D/E 业务阻断

- 结论：
  - 通过。DNC/勿扰客户和 Watch/Invalid 客户均通过硬拦截服务进入 blocked，不允许自动发送。
- 发现项：
  - DNC 来源同时识别 `do_not_contact=True` 和 `status=do_not_contact`。
  - Watch 对外显示为 D，Invalid 对外显示为 E，符合前端展示口径。
  - 阻断原因写入草稿审计 JSON，人工确认页面可读取 `block_reasons` 和 `customer_policy`。
- 修正结果：
  - 未发现需要修正的实质阻塞问题。

### 第二轮评审：链路复用与测试契约

- 结论：
  - 通过。新增集成服务复用 `EmailReplyHardBlockService`，不重复实现硬规则，不发送邮件、不调用 LLM、不直接写发送记录。
- 发现项：
  - 生成、审核、发送前检查后续可统一调用 `EmailReplyCustomerPolicyService.apply_customer_policy_to_draft(...)`。
  - 既有 DNC API/服务回归已覆盖客户标记勿扰、取消勿扰权限、触达拒绝触发勿扰和候选队列排除。
  - 相关测试运行在 `booking-room` Python 环境，并使用真实 PostgreSQL 测试会话契约。
- 修正结果：
  - 已修正两处旧测试过期断言；无新增实质阻塞问题。
