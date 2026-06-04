# E1-S1 Validation：客户主体模型

验证日期：2026-05-28  
Story：`E1-S1 定义客户主体模型`

## 输入包检查

| 项目 | 结果 | 证据 |
|---|---|---|
| Story ID | 通过 | `docs/stories/sprint-3-mvp-data/E1-S1-customer-entity-model.md` |
| 用户价值 | 通过 | Story 用户故事与业务价值已定义 |
| In scope / out of scope | 通过 | 任务清单和非目标已定义 |
| 验收标准 | 通过 | Story 验收标准已定义 |
| 技术栈 | 通过 | Prompt 8 指定 FastAPI、SQLAlchemy/Alembic、PostgreSQL |
| 文档回写点 | 通过 | Story 主文件、本 validation、执行结果、数据字典 |

## 验收映射

| 验收项 | 当前证据 | 结论 |
|---|---|---|
| 客户主体包含名称、国家、城市、客户类型、等级、状态、负责人、勿扰状态 | `apps/api/app/models/customer.py` 包含 `name`、`country`、`city`、`customer_type`、`grade`、`status`、`owner`、`do_not_contact` | 通过 |
| 来源记录可一对多挂到客户主体 | `Customer.sources` 与 `LeadSource.customer_id` | 通过 |
| 联系方式可一对多挂到客户主体 | `Customer.contact_methods` 与 `ContactMethod.customer_id` | 通过 |
| 一个客户可以同时拥有官网、Telegram、VK、邮箱、电话等多个来源或联系方式 | `ContactMethodType` 包含 `website`、`website_form`、`telegram`、`vkontakte`、`email`、`phone` | 通过 |
| 勿扰状态必须属于客户主体级别 | `customers.do_not_contact`、`do_not_contact_reason`、`do_not_contact_marked_by`、`do_not_contact_marked_at` | 通过 |
| 来源证据和 AI 审计不可被合并流程覆盖 | `lead_sources.evidence_note` 与 `ai_audit_logs.input_payload/output_payload` 独立保存 | 通过 |

## 验证命令

```bash
/Users/linhuanbin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m compileall apps/api
```

结果：通过。

```bash
PYTHONPATH=apps/api /Users/linhuanbin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "import apps.api.tests.test_model_contract as m; tests=[name for name in dir(m) if name.startswith('test_')]; [getattr(m,name)() for name in tests]; print(f'model contract tests passed: {len(tests)}')"
```

结果：`model contract tests passed: 6`

```bash
PYTHONPATH=apps/api /Users/linhuanbin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "import apps.api.tests.test_service_rules as m; tests=[name for name in dir(m) if name.startswith('test_')]; [getattr(m,name)() for name in tests]; print(f'service rule tests passed: {len(tests)}')"
```

结果：`service rule tests passed: 4`

## 未执行项

| 项目 | 原因 | 后续补救 |
|---|---|---|
| `pytest` 正式测试运行 | 当前环境未安装 pytest | 安装 `apps/api` 的 test extras 后运行 `pytest apps/api/tests` |
| FastAPI 启动测试 | 当前环境未安装 FastAPI | 安装依赖后运行 `uvicorn app.main:app` |
| SQLAlchemy/Alembic 真实数据库迁移 | 当前环境未安装 SQLAlchemy/Alembic 且未配置 PostgreSQL 实例 | 安装依赖并配置 `VEHICLE_LEADS_DATABASE_URL` 后运行 `alembic upgrade head` |

## 结论

E1-S1 的模型定义、数据字典、迁移草案和核心服务规则已完成。受限于当前依赖环境，已用标准库完成结构与规则验证；真实数据库迁移和 API 运行验证留到依赖安装后的 E1-S2 / Sprint 3 集成验证阶段执行。

