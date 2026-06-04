# Story E1-S1：定义客户主体模型

## 基本信息

- Epic：E1 线索数据模型与同步
- Sprint：Sprint 3 MVP 数据底座
- 优先级：P0
- 状态：Done
- 负责人建议：后端工程 + 产品负责人

## 用户故事

作为研发负责人，我希望客户主体和来源、联系方式分离，以便解决同一个车商出现在多个渠道的问题。

## 业务价值

提升去重质量，避免重复触达和重复交付。

## 依赖

- E0-S1 创建飞书五张表

## 任务清单

- [x] 设计客户主体表。
- [x] 设计来源记录表。
- [x] 设计联系方式表。
- [x] 设计触达记录表。
- [x] 设计 AI 审计日志表。
- [x] 设计合规配置表。
- [x] 定义状态、等级、风险标签枚举。
- [x] 输出 ERD 或数据字典。

## 验收标准

- 客户主体包含名称、国家、城市、客户类型、等级、状态、负责人、勿扰状态。
- 来源记录可一对多挂到客户主体。
- 联系方式可一对多挂到客户主体。
- 一个客户可以同时拥有官网、Telegram、VK、邮箱、电话等多个来源或联系方式。

## 非目标

- MVP 不做复杂企业集团、门店层级和多人联系人关系。

## QA / 风控检查

- [x] 勿扰状态必须属于客户主体级别。
- [x] 来源证据和 AI 审计不可被合并流程覆盖。

## 交付记录

- 交付日期：2026-05-28
- 交付文件：
  - `apps/api/app/models/customer.py`
  - `apps/api/app/models/lead_source.py`
  - `apps/api/app/models/contact_method.py`
  - `apps/api/app/models/outreach_record.py`
  - `apps/api/app/models/ai_audit_log.py`
  - `apps/api/app/models/channel_risk_rule.py`
  - `apps/api/app/models/compliance_review.py`
  - `apps/api/app/models/inventory_item.py`
  - `apps/api/app/models/sync_log.py`
  - `apps/api/alembic/versions/20260528_0001_initial_data_foundation.py`
  - `docs/superpowers/specs/2026-05-28-mvp-data-foundation-data-dictionary.md`
  - `docs/stories/sprint-3-mvp-data/E1-S1-customer-entity-model.validation.md`
- 验收结果：通过。客户主体、来源记录、联系方式、触达记录、AI 审计、合规配置、车源和同步日志模型已建立；客户可挂多个来源和多个联系方式；联系方式枚举支持官网、Telegram、VK、邮箱、电话等。
- 测试结果：
  - `/Users/linhuanbin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m compileall apps/api`，通过。
  - `PYTHONPATH=apps/api ... test_model_contract`，6 个结构测试通过。
  - `PYTHONPATH=apps/api ... test_service_rules`，4 个服务规则测试通过。
- 限制说明：当前环境未安装 FastAPI、SQLAlchemy、Alembic、pytest，因此未执行真实 ORM 建表、Alembic 连接 PostgreSQL 和 FastAPI 启动测试；工程文件已按目标依赖声明，后续安装依赖后可执行。
