# Story P3-E9-S1：最小角色权限与关键动作后端守卫

状态：实现完成，真实 PostgreSQL migration/API 联调待复跑
Sprint：Sprint 9
优先级：P1
Epic：P3-E9

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“最小角色权限与关键动作后端守卫”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 为运营、客服、销售、合规/管理员建立关键动作权限边界。

**Files:**

- Create/Modify: `apps/api/app/services/permissions.py`
- Modify relevant services
- Test: `apps/api/tests/test_phase3_permission_guards.py`

**Codex 提示词：**

```text
请执行 P3-E9-S1：最小角色权限与关键动作后端守卫。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e9-s1-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 恢复 Invalid 仅合规/管理员。
- 取消勿扰仅合规/管理员。
- 疑似重复和客户级归并需管理员。
- 客服/销售不能绕过 C 级合规复核。
- 权限不足返回明确错误。

**非目标：**

- 不做完整 RBAC 配置系统。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 必须执行必要的前后端真实联调，不允许只验证 seed 静态页面。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动触达。
- Forbidden 来源不得作为客户晋级关键来源。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级客户报价、合同、付款、物流、清关、交付周期等动作前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。
- Agent 不得自动晋级客户、自动归并客户、自动恢复 Invalid、自动触达客户。

## 执行记录

执行时间：2026-06-04
执行者：Codex
执行方式：`superpowers:executing-plans` + `superpowers:test-driven-development` + `superpowers:systematic-debugging` + `superpowers:verification-before-completion`

### 实现摘要

- 新增/更新 `apps/api/app/services/permissions.py`，建立固定最小角色权限服务，不引入完整 RBAC。
- 更新 `apps/api/app/services/lead_cleanup.py`，清洗建议 review 和 execute 阶段均接入权限守卫。
- 更新 `apps/api/app/services/customer_dnc.py`、`apps/api/app/api/customers.py`、`apps/api/app/schemas/customer.py`，取消勿扰支持 `actor_role`，仅合规/管理员可执行，权限不足返回 `403`。
- 更新 `apps/api/app/services/compliance.py`、`apps/api/app/api/compliance.py`、`apps/api/app/schemas/compliance.py`，C 级报价前动作支持 `actor_role`，客服/销售未通过合规复核时返回 `403`。
- 更新 `apps/api/tests/test_phase3_permission_guards.py`、`apps/api/tests/test_lead_cleanup_execute_api.py`、`apps/api/tests/test_customer_dnc_api.py`、`apps/api/tests/test_compliance_review_api.py`。

### 验收结果

- 恢复 Invalid 仅合规/管理员：通过，以 `RESTORE_FROM_WATCH` 作为 Watch/Invalid 恢复入口，非合规/管理员被阻断。
- 取消勿扰仅合规/管理员：通过，`CustomerDncService.unmark_do_not_contact` 使用权限服务校验。
- 疑似重复和客户级归并需管理员：通过，review 和 execute 阶段均校验管理员。
- 客服/销售不能绕过 C 级合规复核：通过，`actor_role=sales/customer_service` 且 C 级报价复核未通过时返回权限错误。
- 权限不足返回明确错误：通过，服务层抛出 `PermissionError`，相关 API 层转换为 `403`。
- 非目标“不做完整 RBAC 配置系统”：遵守。

### TDD 记录

红灯 1：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_permission_guards.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.permissions'
```

红灯 2：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_permission_guards.py -q
```

结果：

```text
AttributeError: type object 'Phase3PermissionService' has no attribute 'ensure_cleanup_execution_allowed'
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_permission_guards.py -q
```

结果：

```text
7 passed
```

### 验证命令

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase3_permission_guards.py tests/test_lead_cleanup_review_api.py tests/test_lead_cleanup_execute_api.py tests/test_customer_assignment_status.py tests/test_customer_assignment_compliance_guards.py -q
```

结果：41 passed。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m compileall app/services/permissions.py app/services/lead_cleanup.py app/services/customer_dnc.py app/services/compliance.py app/api/customers.py app/api/compliance.py app/schemas/customer.py app/schemas/compliance.py
```

结果：退出码 0。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
openapi=client.get('/openapi.json').json()
for path in ['/customers/{customer_id}/do-not-contact/cancel','/compliance/customers/{customer_id}/mark-quoted','/lead-cleanup/suggestions/{suggestion_id}/execute']:
    print(path, path in openapi['paths'])
PY
```

结果：三个接口路径均为 `True`。

真实 PostgreSQL API 关联测试：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_customer_dnc_api.py tests/test_compliance_review_api.py -q
```

结果：真实数据库联调未通过。失败发生在 setup 写入 `customers` 时，目标 PostgreSQL 缺少模型已要求的 `customers.owner_team` 列；仓库已有迁移 `apps/api/alembic/versions/20260604_0028_add_customer_owner_team.py`，但目标库未应用。尝试执行 `alembic current` 时，当前沙箱网络策略对 `8.129.17.71:5432` 返回 `PermissionError: [Errno 1] Operation not permitted`，因此无法在本轮完成真实库 migration 复跑。

### 两轮独立评审

第一轮评审：权限边界、服务层守卫、API 错误语义。

结论：通过，无新增阻塞问题。

发现项：

- 只在清洗 review 阶段校验管理员不够，已审批的疑似重复或客户级归并仍可能被运营执行。
- 取消勿扰原请求没有 `actor_role`，无法区分客服/销售与合规/管理员。
- C 级报价前动作原请求没有 `actor_role`，无法区分客服/销售绕过合规复核与普通流程阻断。

修正结果：

- 新增 `Phase3PermissionService.ensure_cleanup_execution_allowed`，清洗 execute 阶段再次校验。
- `DoNotContactRequest` 和 `MarkQuotedRequest` 增加 `actor_role`，服务层和 API 层透传。
- `customers.py` 与 `compliance.py` API 对 `PermissionError` 返回 `403` 和明确错误。

第二轮评审：非目标、风控边界、真实数据库联调状态。

结论：通过，无新增实质阻塞问题；真实 PostgreSQL 联调需在可连接且已应用迁移的环境复跑。

发现项：

- 本 Story 不应扩展成完整 RBAC，也不应新增动态权限表。
- 权限守卫不得改变 raw/staging/core 分层，不得让 Agent 自动晋级、归并、恢复或触达。
- 真实 PostgreSQL 目标库缺少 `owner_team` 迁移列，导致数据库 API 回归无法作为本轮通过证据。

修正结果：

- 权限实现保持固定最小角色集合，未新增 RBAC 配置系统。
- 守卫只作用于人工关键动作入口，未新增 Agent 自动执行能力。
- 已记录真实数据库 migration/API 联调待复跑，不将数据库迁移缺口混同为 P3-E9-S1 权限逻辑失败。

### 结果文档

- `_bmad-output/implementation-artifacts/codex-p3-e9-s1-执行结果.md`
