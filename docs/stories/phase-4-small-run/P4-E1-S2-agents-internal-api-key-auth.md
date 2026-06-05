# Story P4-E1-S2：实现内部 API Key 鉴权

状态：已实现  
Sprint：Sprint 1  
优先级：P0  
Epic：P4-E1

## 用户故事

作为系统维护者，我希望 `apps/agents` 的 Agent Run API 需要内部 API Key，以便同机独立端口也具备基础服务边界保护。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 为 `apps/agents` 实现 `X-Agents-Api-Key` 校验依赖。

**建议文件：**

- Create/Modify: `apps/agents/app/settings.py`
- Create/Modify: `apps/agents/app/security.py`
- Modify: `apps/agents/app/main.py`
- Test: `apps/agents/tests/test_internal_api_key_auth.py`

**验收标准：**

- 缺少 `X-Agents-Api-Key` 的受保护请求返回 401。
- API Key 错误的受保护请求返回 401。
- API Key 正确的受保护请求可继续执行。
- `/health` 可保持无需鉴权或明确记录鉴权策略。

**非目标：**

- 不实现用户级 JWT。
- 不实现 RBAC。
- 不接入外部身份系统。

## Codex 提示词

```text
请执行 P4-E1-S2：实现 apps/agents 内部 API Key 鉴权。
要求使用 TDD；只实现内部服务鉴权；用户权限仍由 apps/api 控制；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/agents` 不暴露公网服务。
- `apps/agents` 不写 core 业务表。

## 执行记录

执行日期：2026-06-05  
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md` 执行当前 Story。

### Git / Worktree 记录

- 延续 `P4-E1-S1` 的环境事实：当前沙箱禁止写 `.git/FETCH_HEAD` 和 `.git/refs/heads/*.lock`。
- 因此无法在本环境完成 `git fetch`、创建分支和 worktree。
- 按 `superpowers:using-git-worktrees` 的 sandbox fallback，在当前工作区继续执行本 Story。
- 未执行 git 提交。

### TDD 记录

红灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_internal_api_key_auth.py -q
```

结果：失败，原因是 `ModuleNotFoundError: No module named 'app.security'`，符合当前 Story 需要新增内部 API Key 鉴权依赖的预期。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_internal_api_key_auth.py -q
```

结果：`4 passed in 0.17s`。

### 实现摘要

- 新增 `apps/agents/app/settings.py`，读取 `AGENTS_API_KEY`。
- 新增 `apps/agents/app/security.py`，提供 `require_internal_api_key` FastAPI 依赖。
- 使用 `X-Agents-Api-Key` header 校验内部服务 API Key。
- 缺少 API Key 或 API Key 错误时返回 401。
- API Key 正确时允许受保护请求继续执行。
- `/health` 保持公开，无需鉴权。
- 未实现用户级 JWT。
- 未实现 RBAC。
- 未接入外部身份系统。
- 未实现 Agent Run API。

### 验证命令

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_health_api.py tests/test_internal_api_key_auth.py -q
```

结果：`6 passed in 0.17s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

结果：`23 passed in 0.19s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.security import require_internal_api_key
from app.settings import get_settings
import os
os.environ['AGENTS_API_KEY'] = 'manual-check'
get_settings.cache_clear()
app = FastAPI()
@app.get('/protected', dependencies=[Depends(require_internal_api_key)])
def protected():
    return {'ok': True}
client = TestClient(app)
print(client.get('/protected').status_code)
print(client.get('/protected', headers={'X-Agents-Api-Key': 'bad'}).status_code)
print(client.get('/protected', headers={'X-Agents-Api-Key': 'manual-check'}).status_code)
PY
```

结果：

```text
401
401
200
```

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.main import app
print(app.title)
print(len(app.routes) > 0)
PY
```

执行目录：`apps/api`  
结果：

```text
Overseas Vehicle Leads AI API
True
```

## 两轮独立评审记录

### 第一轮评审：需求、鉴权、安全边界

结论：

- 通过。已实现 `X-Agents-Api-Key` 校验依赖。
- 通过。缺少 API Key 的受保护请求返回 401。
- 通过。API Key 错误的受保护请求返回 401。
- 通过。API Key 正确的受保护请求可继续执行。
- 通过。`/health` 明确保持公开。
- 通过。未实现用户级 JWT、RBAC 或外部身份系统。

发现项：

- 当前 Story 尚无真实 Agent Run API 可挂载鉴权依赖，因此使用测试中的临时受保护路由验证依赖行为。

修正结果：

- 已在测试中直接覆盖 `require_internal_api_key` 依赖的三类鉴权行为；真实 Agent Run API 将在后续 Story 创建时挂载该依赖。

### 第二轮评审：回归、架构、可运维性

结论：

- 通过。`apps/agents` 全量测试通过：`23 passed in 0.19s`。
- 通过。`apps/api` 可导入自身 `app.main`，现有 LLM Agent 行为未被触碰。
- 通过。鉴权只校验可信内部服务身份，不引入用户级权限，用户权限仍由 `apps/api` 控制。
- 通过。`apps/agents` 未写 core 业务表，未暴露公网服务相关配置。
- 通过。API Key 未记录到日志或响应体。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
