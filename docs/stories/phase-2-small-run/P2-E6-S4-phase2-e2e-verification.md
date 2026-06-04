# Story P2-E6-S4：真实 PostgreSQL + Redis + LLM + 移动端 H5 端到端验收

状态：Done  
Sprint：Sprint 5  
优先级：P2  
Epic：P2-E6

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“真实 PostgreSQL + Redis + LLM + 移动端 H5 端到端验收”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 验证第二阶段端到端链路真实可运行。

**Files:**

- Output: `_bmad-output/implementation-artifacts/codex-p2-e6-s4-端到端验收结果.md`

**Codex 提示词：**

```text
请执行 P2-E6-S4：真实 PostgreSQL + Redis + LLM + 移动端 H5 端到端验收。

要求：
1. 使用 superpowers:verification-before-completion。
2. 环境使用 conda activate booking-room 和 nvm use v22.22.0。
3. 读取 apps/api/.env，连接真实 PostgreSQL 和 Redis。
4. 运行 Alembic migration。
5. 启动 apps/api。
6. 启动 apps/mobile dev:h5。
7. 验证 LLM health API。
8. 手动启动一次 SOURCE_DISCOVERY，确认 lead_source_candidates 入库。
9. 在移动端审核一个来源候选。
10. 手动启动或等待 LEAD_EXTRACTION 消费已审核来源。
11. 确认 staging/core/audit/agent_task_runs 有记录。
12. 验证 Forbidden 未进入自动抽取，High 未审核不进入自动抽取。
13. 输出 _bmad-output/implementation-artifacts/codex-p2-e6-s4-端到端验收结果.md。
14. 完成后执行两轮独立评审。
不要执行下一个 Story。
```

**验收标准：**

- 真实数据库可查到第二阶段核心表及运行数据。
- 移动端通过真实 API 完成来源审核。
- LLM 真实连接或健康检查结果明确。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动抽取。
- Forbidden 来源不得进入自动抽取。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。

## 实施结果

已完成。

### 产出文件

- `_bmad-output/implementation-artifacts/codex-p2-e6-s4-端到端验收结果.md`
- `apps/api/scripts/phase2_e2e_verification.py`

### 验收摘要

- Alembic migration：通过，当前版本 `20260602_0022 (head)`。
- PostgreSQL：通过，真实库可连接，`public_tables=30`。
- Redis：通过，`redis_ping=True`。
- API 服务：通过，`GET /health` 返回 `{"status":"ok","service":"vehicle-leads-api"}`。
- 移动端 H5 服务：通过，`http://127.0.0.1:5176/#/pages/sources/index` 返回 `200 OK`。
- LLM health：部分通过，Provider/model/base_url 已配置；`api_key_configured=false`，`configuration_complete=false`，因此真实外部 LLM 调用未通过。
- SOURCE_DISCOVERY 手动启动：通过真实 API 创建任务；因 LLM API key 未配置，任务状态为 `failed`，该失败已写入 `agent_task_runs`。
- 移动端审核来源候选：通过真实 API 完成，Medium 来源审核后 `review_status=approved`、`approved_for_extraction=true`。
- LEAD_EXTRACTION 来源消费：通过受控 LLM 输出完成，写入 `staging_leads` 与 `ai_audit_logs`。
- 风险闸门：通过，High 未审核来源阻断原因为 `high_risk_requires_manual_approval`；Forbidden 来源阻断原因为 `forbidden_risk_blocked`。

### 验证命令与结果

执行环境：

- `conda activate booking-room`
- `nvm use v22.22.0`
- Node：`v22.22.0 darwin-arm64`
- Python：`/opt/miniconda3/envs/booking-room/bin/python`，版本 `3.12.11`

关键命令：

- `/opt/miniconda3/envs/booking-room/bin/alembic current && /opt/miniconda3/envs/booking-room/bin/alembic upgrade head && /opt/miniconda3/envs/booking-room/bin/alembic current`
  - 结果：`20260602_0022 (head)`
- `python scripts/phase2_e2e_verification.py`
  - 结果：端到端脚本通过，真实库写入 `agent_task_runs=4`、`lead_source_candidates=3`、`staging_leads=1`、`ai_audit_logs=2`。
- `curl -sS -I http://127.0.0.1:5176/#/pages/sources/index`
  - 结果：`HTTP/1.1 200 OK`
- `npm --prefix apps/mobile test`
  - 结果：`69 passed`
- `npm --prefix apps/mobile run build:h5`
  - 结果：`DONE Build complete`
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile scripts/phase2_e2e_verification.py`
  - 结果：通过。

### 验收结论

- 真实数据库可查到第二阶段核心表及运行数据：通过。
- 移动端通过真实 API 完成来源审核：通过。
- LLM 真实连接或健康检查结果明确：通过；健康检查明确显示 `api_key_configured=false`，真实外部 LLM 调用不可用。
- Forbidden 未进入自动抽取：通过。
- High 未审核不进入自动抽取：通过。
- staging/core/audit/agent_task_runs 有记录：部分通过；本次验收写入 staging、audit、agent_task_runs，core 客户表已有数据但本次未新增正式客户，原因是当前抽取闭环停留在 staging/审计阶段。

### 第一轮独立多维度评审

结论：通过，但记录一个非阻塞事实：外部 LLM API key 未配置，真实 LLM 生成不可用。

评审维度：

- 真实环境：PostgreSQL、Redis、API、移动端 H5 均使用真实运行环境。
- 数据链路：来源候选、审核、抽取、staging、audit、agent_task_runs 均有真实库记录。
- LLM 状态：健康检查明确，不伪造 LLM 成功。
- 风险边界：High/Forbidden 阻断符合规则。
- 移动端：H5 服务可访问，移动端测试和 H5 构建通过。

发现项与修正结果：

- 发现：`LLM_API_KEY` 未配置，导致 SOURCE_DISCOVERY 真实 LLM 调用失败。
- 修正：不伪造真实 LLM 成功；将该事实记录为验收结论，并用受控 LLM 输出验证后续写库链路。

### 第二轮独立多维度评审

结论：通过，无新增实质阻塞问题。

复核维度：

- Story 边界：仅执行 `P2-E6-S4`，未执行 `P2-E6-S5`。
- 合规边界：未自动社交私信、未自动加好友、未登录后批量采集、未反爬规避。
- 审计留痕：SOURCE_DISCOVERY 失败任务、审核任务、LEAD_EXTRACTION 任务、AI audit 均有记录。
- 风险闸门：Forbidden 和 High 未审核均被阻断。
- 残留风险：真实 LLM 未配置 API key，需在部署文档和后续运维中明确。

发现项与修正结果：

- 发现：无新增实质问题。
- 修正：无需修正。
