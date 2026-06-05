# Story P4-E1-S4：补充本地启动文档和端口配置

状态：已实现  
Sprint：Sprint 1  
优先级：P1  
Epic：P4-E1

## 用户故事

作为第四阶段运行人员，我希望清楚知道如何同时启动 `apps/api:8000` 和 `apps/agents:8010`，以便完成本地小范围服务间联调。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/x-agent-deploy.md`

## Story 定义

**目标：** 补充第四阶段本地运行手册和端口配置说明。

**建议文件：**

- Modify: `apps/agents/README.md`
- Modify: `docs/x-agent-deploy.md`
- Create/Modify: `docs/stories/phase-4-small-run/README.md`

**验收标准：**

- 文档说明 `apps/api` 使用 `8000`，`apps/agents` 使用 `8010`。
- 文档说明 `AGENTS_BASE_URL=http://127.0.0.1:8010`。
- 文档说明 `AGENTS_API_KEY` 配置方式。
- 文档说明第四阶段不使用 Docker Compose 作为必需项。

**非目标：**

- 不实现代码。
- 不引入容器编排。

## Codex 提示词

```text
请执行 P4-E1-S4：补充第四阶段本地启动文档和端口配置。
要求保持中文文档；不实现代码；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 文档不得建议把 `apps/agents` 暴露公网。
- 文档不得建议 `apps/api` 本地包注入 `apps/agents`。

## 执行记录

执行日期：2026-06-05  
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md` 执行当前 Story。

### Git / Worktree 记录

- 延续当前环境事实：沙箱禁止写 `.git/FETCH_HEAD` 和 `.git/refs/heads/*.lock`。
- 无法在本环境完成 `git fetch`、创建分支和 worktree。
- 按 `superpowers:using-git-worktrees` 的 sandbox fallback，在当前工作区继续执行本 Story。
- 未执行 git 提交。

### 实现摘要

- 更新 `apps/agents/README.md`，补充第四阶段定位、本地启动方式、端口、API Key、健康检查、OpenAPI 和运行边界。
- 更新 `docs/x-agent-deploy.md`，新增 `5.12 第四阶段 apps/agents 本地小范围运行`。
- 更新 `docs/stories/phase-4-small-run/README.md`，补充第四阶段本地运行约定。
- 明确 `apps/api` 默认端口为 `8000`。
- 明确 `apps/agents` 默认端口为 `8010`。
- 明确 `AGENTS_BASE_URL=http://127.0.0.1:8010`。
- 明确 `AGENTS_API_KEY` 配置方式和 `X-Agents-Api-Key` header。
- 明确 `/health` 保持公开。
- 明确第四阶段本地小范围运行不要求 Docker Compose。
- 明确不得把 `apps/agents` 暴露公网，不得让前端或外部客户端直接调用。
- 明确 `apps/api` 通过 HTTP API 调用 `apps/agents`，不得本地包注入。

### 验证命令

```bash
rg -n "8000|8010|AGENTS_BASE_URL=http://127\\.0\\.0\\.1:8010|AGENTS_API_KEY|X-Agents-Api-Key|Docker Compose|公网|本地包|前端或外部客户端|/health" apps/agents/README.md docs/x-agent-deploy.md docs/stories/phase-4-small-run/README.md
```

结果：三份文档均命中端口、环境变量、API Key、Docker Compose 非必需、公网暴露禁令、本地包注入禁令和 `/health` 策略。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

执行目录：`apps/agents`  
结果：`28 passed in 0.22s`。

### 结构修正

第一次写入 `docs/x-agent-deploy.md` 时，第四阶段小节插入在第二阶段 APScheduler 小节的“启用前必须满足：”之后，打断了原有列表。

修正结果：

- 已将 `5.12 第四阶段 apps/agents 本地小范围运行` 移动到第二阶段 APScheduler 小节结束后的独立小节。
- 原 `5.11 第二阶段 APScheduler 与 Redis Lock` 的启用条件、配置开关和限制说明保持连续。

## 两轮独立评审记录

### 第一轮评审：文档覆盖与验收标准

结论：

- 通过。文档已说明 `apps/api` 使用 `8000`，`apps/agents` 使用 `8010`。
- 通过。文档已说明 `AGENTS_BASE_URL=http://127.0.0.1:8010`。
- 通过。文档已说明 `AGENTS_API_KEY` 和 `X-Agents-Api-Key` 配置方式。
- 通过。文档已说明第四阶段本地小范围运行不要求 Docker Compose。
- 通过。`/health` 公开策略已明确。

发现项：

- 初次插入 `docs/x-agent-deploy.md` 的位置打断了第二阶段 APScheduler 小节。

修正结果：

- 已移动第四阶段小节，保持部署文档结构连续。

### 第二轮评审：边界、回归、可执行性

结论：

- 通过。文档未建议把 `apps/agents` 暴露公网。
- 通过。文档未建议 `apps/api` 本地包注入 `apps/agents`，反而明确禁止。
- 通过。文档明确前端和外部客户端不得直接调用 `apps/agents`。
- 通过。没有引入 Docker Compose 或容器编排实现。
- 通过。本 Story 未改动业务代码；`apps/agents` 全量测试通过：`28 passed in 0.22s`。

发现项：

- 当前沙箱仍不允许绑定本地端口，真实 `8010` 监听需在非沙箱环境复验。该限制已在 `P4-E1-S1` 记录。

修正结果：

- 无需修正；本 Story 是文档 Story，已明确本地启动命令和复验方式。
