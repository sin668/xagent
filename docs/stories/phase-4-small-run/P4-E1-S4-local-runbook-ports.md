# Story P4-E1-S4：补充本地启动文档和端口配置

状态：待实现  
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

