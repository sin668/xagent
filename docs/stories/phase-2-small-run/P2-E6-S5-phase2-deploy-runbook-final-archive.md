# Story P2-E6-S5：部署与运行手册、最终验收结果归档

状态：Done  
Sprint：Sprint 5  
优先级：P2  
Epic：P2-E6

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“部署与运行手册、最终验收结果归档”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 输出第二阶段部署、运行、调度、回滚和风险处理说明。

**Files:**

- Create: `docs/deploy/2026-06-02-第二阶段小范围运行部署与运行手册.md`
- Create: `_bmad-output/implementation-artifacts/codex-p2-final-验收归档.md`

**Codex 提示词：**

```text
请执行 P2-E6-S5：部署与运行手册、最终验收结果归档。

要求：
1. 使用 superpowers:verification-before-completion。
2. 输出 docs/deploy/2026-06-02-第二阶段小范围运行部署与运行手册.md。
3. 文档包含环境变量、PostgreSQL migration、Redis、LLM Provider、APScheduler 开关、移动端 H5、管理后台、常见故障、风险暂停和恢复流程。
4. 输出 _bmad-output/implementation-artifacts/codex-p2-final-验收归档.md。
5. 归档必须列出已完成 Story、测试结果、联调结果、未完成项、残留风险。
6. 完成后执行两轮独立评审。
不要继续扩展新功能。
```

**验收标准：**

- 部署与运行手册可指导本机或服务器运行。
- 最终验收归档完整。

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

新增文件：

- `docs/deploy/2026-06-02-第二阶段小范围运行部署与运行手册.md`
- `_bmad-output/implementation-artifacts/codex-p2-final-验收归档.md`
- `_bmad-output/implementation-artifacts/codex-p2-e6-s5-执行结果.md`

修改文件：

- `docs/x-p1-deploy.md`
- `docs/stories/phase-2-small-run/P2-E6-S5-phase2-deploy-runbook-final-archive.md`

实施内容：

- 输出第二阶段小范围运行部署与运行手册，覆盖环境变量、PostgreSQL migration、Redis、LLM Provider、APScheduler、移动端 H5、管理后台、常见故障、风险暂停和恢复流程。
- 输出第二阶段最终验收归档，列出 29 个已完成 Story、测试结果、联调结果、未完成项和残留风险。
- 补充 P1 部署文档中的第二阶段 LLM Agent 启动、定时、健康检查、审计和暂停恢复说明。
- 明确真实外部 LLM 只有在 `/llm-health.configuration_complete=true` 后才可认定可用。
- 明确当前 APScheduler 默认 handler 为 placeholder，启用定时前必须接入真实 handler。

## 验证结果

- 部署与运行手册已创建：通过。
- 最终验收归档已创建：通过。
- 文档覆盖 Story 要求的环境变量、migration、Redis、LLM Provider、APScheduler、移动端、后台、常见故障、暂停恢复流程：通过。
- 归档覆盖已完成 Story、测试结果、联调结果、未完成项和残留风险：通过。
- 未扩展新功能：通过。
- 未执行下一个 Story：通过。

## 第一轮独立多维度评审

结论：通过，无新增实质阻塞问题。

评审维度：

- 需求覆盖：已覆盖 Story 的两个目标文件和全部验收要求。
- 技术准确性：部署文档中的 API 路由、环境变量、scheduler job、Redis lock、LLM health 均基于代码核查。
- 合规边界：明确不自动社交私信、不自动加好友、不登录后批量采集、不反爬规避。
- 运维可执行性：包含手动启动、健康检查、SQL 核查、故障处理、暂停和恢复流程。

发现项与修正结果：

- 发现：必须避免把受控 LLM 输出验证误写成真实外部 LLM 已成功。
- 修正：文档明确 `LLM_API_KEY` 未配置时真实外部 LLM 不可用，只有 `/llm-health.configuration_complete=true` 后才可认定可用。

## 第二轮独立多维度评审

结论：通过，无新增实质阻塞问题。

复核维度：

- 范围控制：仅执行 `P2-E6-S5`，未新增功能代码。
- BMAD 留痕：Story、执行结果、最终归档和部署手册均已落盘。
- 风险收口：LLM API key、APScheduler placeholder、High/Forbidden、勿扰和 C 级复核均有明确边界。
- 可交付性：文档可指导本机或服务器完成第二阶段试运行部署和核查。

发现项与修正结果：

- 发现：无新增实质问题。
- 修正：无需修正。
