# XAgent - 海外车辆采购 AI 获客系统 P1 部署文档

> 版本: 1.0 | 更新: 2026-06-04 | 阶段: PoC → MVP
> 本次更新: 第 8.2 节补充当前数据库 35 张表的分组清单、用途说明和核心字段。

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [环境要求](#2-环境要求)
3. [基础设施准备](#3-基础设施准备)
4. [apps/api 部署 (FastAPI 后端)](#4-appsapi-部署-fastapi-后端)
5. [LLM 对接配置 (核心)](#5-llm-对接配置-核心)
6. [apps/admin 部署 (Vue3 管理后台)](#6-appsadmin-部署-vue3-管理后台)
7. [apps/mobile 部署 (uni-app H5)](#7-appsmobile-部署-uni-app-h5)
8. [数据库初始化与迁移](#8-数据库初始化与迁移)
9. [Seed 数据导入](#9-seed-数据导入)
10. [环境变量清单](#10-环境变量清单)
11. [日常运维操作](#11-日常运维操作)
12. [合规红线与安全约束](#12-合规红线与安全约束)

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Mobile H5    │  │  Admin 后台   │  │  飞书多维表格 (数据源) │   │
│  │  :5176        │  │  :5174        │  │  (Bitable API)       │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                      │               │
├─────────┴─────────────────┴──────────────────────┴───────────────┤
│                        API 网关层                                   │
│              FastAPI (:8000) + CORS                                 │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  18 个 Router (customers, channel-risk, inventory,       │     │
│  │  llm-lead-extraction, llm-lead-grading, outreach, etc.)  │     │
│  └──────────────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────┤
│                       服务层                                       │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐    │
│  │ LLM 抽取  │ │ LLM 分级  │ │ RAG 上下文 │ │ 触达草稿生成      │    │
│  │ Service  │ │ Service  │ │ Service   │ │ Service         │    │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └────────┬─────────┘    │
│       │            │             │                  │              │
├───────┴────────────┴─────────────┴──────────────────┴──────────────┤
│                      外部 LLM 接入层                                │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  LLM Provider API (Anthropic / OpenAI / 其他兼容接口)     │     │
│  │  Prompt 管理 + 版本控制 + Token 计量 + 费用审计            │     │
│  └──────────────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────┤
│                       数据层                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │ PostgreSQL    │  │ Redis        │  │ pgvector 扩展    │       │
│  │ 14+ (主库)    │  │ 6+ (缓存)     │  │ (向量搜索/RAG)   │       │
│  └──────────────┘  └──────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 核心数据流

```
公开网页 → PublicPageRead → LLM Lead Extraction → LLM Lead Grading
     → Human Review → Customer (正式客户)
     → Compliance Review (C 级) → Outreach Draft → Manual Send
```

### LLM 任务类型

| 任务类型 | 说明 | Prompt 版本 | RAG 知识库 |
|---------|------|------------|-----------|
| `LEAD_EXTRACTION` | 从公开文本提取客户信息 | `lead-extraction-v1` | keyword_library, channel_sop |
| `LEAD_GRADING` | 评估线索等级 (A/B/C/Invalid/Watch) | `lead-grading-v1` | compliance_rules, failed_cases, channel_sop |
| `OUTREACH_DRAFT` | 生成俄语触达草稿 | `outreach-template-v1` | faq, script_template, compliance_rules |
| `INVENTORY_MATCHING` | 车源-客户匹配 | (规划中) | - |
| `RISK_BLOCK` | 风险阻断记录 | - | - |

---

## 2. 环境要求

### 服务器资源 (最小配置)

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04 / CentOS 8+ | Ubuntu 22.04 LTS |

### 软件依赖

| 软件 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | API 后端运行时 |
| Node.js | v22+ | Admin / Mobile 构建 |
| PostgreSQL | 14+ | 主数据库 |
| Redis | 6+ | 缓存 / 会话 |
| pgvector | 0.5+ | PostgreSQL 向量搜索扩展 |
| Nginx | 1.24+ (可选) | 反向代理 |

---

## 3. 基础设施准备

### 3.1 PostgreSQL + pgvector

```bash
# 安装 PostgreSQL
sudo apt install postgresql-14 postgresql-server-dev-14

# 安装 pgvector 扩展
sudo apt install postgresql-14-pgvector
# 或从源码编译:
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector && make && sudo make install

# 创建数据库和用户
sudo -u postgres psql <<EOF
CREATE USER xagent WITH PASSWORD 'your_secure_password';
CREATE DATABASE xagent OWNER xagent;
\c xagent
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF
```

### 3.2 Redis

```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 配置密码 (推荐)
echo "requirepass your_redis_password" | sudo tee -a /etc/redis/redis.conf
sudo systemctl restart redis-server
```

---

## 4. apps/api 部署 (FastAPI 后端)

### 4.1 项目结构

```
apps/api/
├── app/
│   ├── main.py              # FastAPI 应用入口, 18 个 Router 注册
│   ├── settings.py          # Pydantic Settings 环境配置
│   ├── models/              # SQLAlchemy 2.0 ORM 模型 (33 张业务运行表)
│   │   ├── enums.py         # 全部枚举定义
│   │   └── ...
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── api/                 # 路由层 (18 个 Router)
│   │   ├── customers.py
│   │   ├── channel_risk.py
│   │   ├── channel_plans.py
│   │   ├── channel_discovery.py
│   │   ├── compliance.py
│   │   ├── dashboard.py
│   │   ├── failed_cases.py
│   │   ├── inventory.py
│   │   ├── knowledge.py
│   │   ├── llm_lead_extraction.py
│   │   ├── llm_lead_grading.py
│   │   ├── outreach_drafts.py
│   │   ├── public_page_read.py
│   │   ├── raw_collection.py
│   │   ├── risk_events.py
│   │   ├── staging_leads.py
│   │   ├── sync.py
│   │   └── ...
│   ├── services/            # 业务逻辑层 (核心)
│   │   ├── llm_lead_extraction.py   # LLM 抽取服务
│   │   ├── llm_lead_grading.py      # LLM 分级服务
│   │   ├── rag_prompt_context.py    # RAG 上下文构建
│   │   ├── public_page_read_agent.py # 公开页面读取
│   │   ├── outreach_draft.py        # 触达草稿生成
│   │   ├── knowledge_search.py      # 向量+关键词搜索
│   │   ├── channel_risk.py          # 渠道风险验证
│   │   ├── raw_collection.py        # 原始数据采集
│   │   ├── audit_risk.py            # 审计日志
│   │   ├── failed_cases.py         # 失败案例
│   │   └── staging_leads.py         # 暂存线索
│   ├── db/                  # 数据库基类和类型
│   │   ├── base.py
│   │   └── types.py         # JSONB, Vector(1536) 自定义类型
│   └── ...
├── alembic/                 # 数据库迁移脚本
│   ├── env.py
│   └── versions/            # 28 个迁移版本
├── alembic.ini
├── pyproject.toml
├── .env                     # 环境变量 (不入库)
└── tests/                   # 50+ 测试文件
```

### 4.2 安装依赖

```bash
cd apps/api

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[test]"

# 验证安装
python -c "from app.main import app; print('OK:', app.title)"
```

### 4.3 配置 .env

```bash
# === 数据库 ===
DATABASE_URL=postgresql+asyncpg://xagent:your_secure_password@localhost:5432/xagent

# === Redis (可选, 用于缓存) ===
REDIS_URL=redis://:your_redis_password@localhost:6379/0

# === 飞书集成 (可选, 用于数据同步) ===
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_BITABLE_APP_TOKEN=your_bitable_token

# === CORS 跨域配置 ===
CORS_ORIGINS=http://localhost:5176,http://127.0.0.1:5176,http://localhost:5174,http://127.0.0.1:5174

# === LLM 配置 (详见第 5 节) ===
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxx
LLM_DEFAULT_MODEL=claude-sonnet-4-6
LLM_EXTRACTION_MODEL=claude-sonnet-4-6
LLM_GRADING_MODEL=claude-sonnet-4-6
LLM_OUTREACH_MODEL=claude-haiku-4-5
```

### 4.4 启动服务

```bash
cd apps/api

# 开发模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 4.5 API 端点总览

| Router | 前缀 | 核心端点 | 说明 |
|--------|------|---------|------|
| `customers` | `/api/customers` | GET/POST | 客户管理, 触达候选, 勿扰标记 |
| `channel_risk` | `/api/channel-risk` | GET/POST/PUT/DELETE | 渠道风险规则管理 |
| `channel_plans` | `/api/channel-plans` | GET/POST/PUT/DELETE | 渠道采集计划 |
| `channel_discovery` | `/api/channel-discovery` | GET/POST | 渠道发现任务 |
| `compliance` | `/api/compliance` | GET/POST/PUT | 合规审核 |
| `dashboard` | `/api/dashboard` | GET | 统计概览, 活动日志, 风险事件 |
| `failed_cases` | `/api/failed-cases` | GET/POST | 失败案例库 |
| `inventory` | `/api/inventory` | GET/POST/PUT | 车源管理, AI 报价安全检查 |
| `knowledge` | `/api/knowledge` | GET/POST | 知识库 (RAG), 集合/条目管理 |
| `llm_lead_extraction` | `/api/llm-lead-extraction` | POST `/extract`, `/batch-extract` | **LLM 线索抽取** |
| `llm_lead_grading` | `/api/llm-lead-grading` | POST `/grade`, `/batch-grade` | **LLM 线索分级** |
| `outreach_drafts` | `/api/outreach-drafts` | GET/POST | 触达草稿, 人工发送记录 |
| `public_page_read` | `/api/public-page-read` | POST `/read` | 公开页面读取 |
| `raw_collection` | `/api/raw-collection` | GET/POST | 原始数据采集 |
| `risk_events` | `/api/risk-events` | GET/POST/PUT | 风险事件管理 |
| `staging_leads` | `/api/staging-leads` | GET/POST/PUT | 暂存线索审核 |
| `sync` | `/api/sync` | GET/POST | 飞书数据同步 |
| health | `/health` | GET | 健康检查 |

### 4.6 验证部署

```bash
# 健康检查
curl http://localhost:8000/health
# 预期: {"status": "ok", "service": "vehicle-leads-api"}

# 查看 API 文档
open http://localhost:8000/docs  # Swagger UI
```

---

## 5. LLM 对接配置 (核心)

### 5.1 架构设计

当前系统采用 **LLM-as-a-Judge + 规则引擎** 的混合架构:

```
用户/API 请求
    │
    ├──① 构建输入 ──→ RAG 上下文注入 + Prompt 组装
    │
    ├──② 调用 LLM ──→ LLM Provider API (Anthropic/OpenAI)
    │                    返回: JSON 结构化输出
    │
    ├──③ 校验输出 ──→ Schema 校验 + 证据验证 + 反编造检查
    │                    (Service 层硬规则, 不依赖 LLM)
    │
    ├──④ 审计记录 ──→ AIAuditLog (全量保存 input/output)
    │                    Token 计量 + 费用追踪
    │
    └──⑤ 业务写入 ──→ StagingLead / Customer 等表
```

**关键设计原则:**
- LLM 只做信息抽取和分级推荐, **不直接写入业务表**
- 所有 LLM 输出必须经过 Service 层硬规则校验 (schema, 证据, 风险阻断)
- 合规硬规则由代码执行, RAG 仅作为上下文增强
- 每次调用全量审计 (input_payload, output_json, tokens, cost)

### 5.2 当前 LLM 调用模式

系统当前使用 **间接调用模式**: API 接收已完成的 LLM 输出 JSON, 负责校验和入库, 而非直接调用 LLM API。

```
外部 LLM 调用 (人工触发 / 定时脚本 / 前端调用)
    │
    └──→ POST /api/llm-lead-extraction/extract
         Body: { candidate_url_id, llm_output_json: { ... } }
              │
              └── Service 校验 → 写入 StagingLead + AIAuditLog
```

### 5.3 LLM 输入输出 Schema

#### Lead Extraction 输入 (传给 LLM)

```json
{
  "task_type": "lead_extraction",
  "schema_version": "poc-ai-output-v1",
  "source": {
    "source_url": "https://dealer.example.ru",
    "platform": "OFFICIAL_WEBSITE",
    "risk_level": "Low"
  },
  "public_text": "<从公开页面提取的文本, 最多 2000 字符>",
  "rag_context": {
    "context_status": "ready",
    "knowledge_item_refs": [...],
    "context_text": "[keyword_library] ...\n[channel_sop] ..."
  }
}
```

#### Lead Extraction 输出 (LLM 返回)

```json
{
  "schema_version": "poc-ai-output-v1",
  "task_type": "lead_extraction",
  "risk_blocked": false,
  "source": {
    "source_url": "https://dealer.example.ru"
  },
  "lead": {
    "customer_name": "AutoCity Moscow",
    "country": "Russia",
    "city": "Moscow",
    "customer_type": "LOCAL_DEALER_SECONDARY_DEALER",
    "activity_signal": "每周更新库存",
    "scale_signal": "展示 50+ 车辆",
    "import_used_relevance": "高",
    "contacts": {
      "emails": ["sales@autocity.ru"],
      "phones": ["+7 495 1234567"],
      "whatsapp": [],
      "telegram": ["@autocity_sales"],
      "wechat": [],
      "website_forms": ["https://autocity.ru/contact"]
    },
    "source_evidence": [
      {
        "claim": "经销商名称",
        "evidence_text": "AutoCity Moscow - официальный дилер подержанных автомобилей",
        "source_url": "https://dealer.example.ru"
      }
    ],
    "missing_fields": ["具体经营年限", "进口车比例"]
  },
  "audit": {
    "model": "claude-sonnet-4-6",
    "prompt_version": "lead-extraction-v1",
    "input_saved": true,
    "output_saved": true,
    "executed_at": "2026-06-01T10:00:00Z"
  }
}
```

#### Lead Grading 输出 (LLM 返回)

```json
{
  "schema_version": "poc-ai-output-v1",
  "task_type": "lead_grading",
  "recommended_grade": "B",
  "recommended_reason": "客户展示完整库存和公开联系方式, 有明确经营信号",
  "reason_codes": ["has_public_inventory", "has_contact_methods", "active_listing"],
  "evidence_refs": [
    {
      "claim": "展示 50+ 车辆库存",
      "evidence_text": "На нашем сайте представлено более 50 автомобилей...",
      "source_url": "https://dealer.example.ru"
    }
  ],
  "missing_fields": ["具体经营年限"],
  "next_action": "handoff_to_customer_service",
  "suggested_handoff_team": "customer_service",
  "touch_queue_allowed": true,
  "touch_channel_limit": "manual_only_low_medium_risk",
  "compliance_review_required": false,
  "human_review_required": true,
  "risk_flags": [],
  "audit": {
    "model": "claude-sonnet-4-6",
    "prompt_version": "lead-grading-v1",
    "input_saved": true,
    "output_saved": true,
    "executed_at": "2026-06-01T10:01:00Z"
  }
}
```

### 5.4 Prompt 模板管理

Prompt 文件位于项目根目录 `prompts/`:

| 文件 | 用途 | 版本 | RAG 依赖 |
|------|------|------|---------|
| `prompts/lead-extraction.md` | 线索抽取 | `lead-extraction-v1` | keyword_library, channel_sop |
| `prompts/lead-grading.md` | 线索分级 | `lead-grading-v1` | compliance_rules, failed_cases, channel_sop |

#### Prompt 调用流程

```
1. 从 prompts/ 加载对应 prompt 模板
2. RAGPromptContextService.build_context() 注入知识库上下文
   - LEAD_EXTRACTION → 搜索 keyword_library + channel_sop 集合
   - LEAD_GRADING → 搜索 compliance_rules + failed_cases + channel_sop 集合
   - 每个集合最多返回 3 条, 每条截断 700 字符
3. 组装: System Prompt + RAG Context + User Prompt (含公开文本)
4. 调用 LLM API → 返回 JSON
5. Service 层校验 (schema_version, evidence, contacts, risk)
6. 审计入库 (AIAuditLog: input_payload, output_json, tokens, cost)
```

### 5.5 LLM 硬规则校验 (代码层, 非 LLM 判断)

抽取服务 (`llm_lead_extraction.py`) 校验:
- `schema_version` 必须为 `poc-ai-output-v1`
- `task_type` 必须为 `lead_extraction`
- `source_url` 必须与候选来源一致
- **High/Forbidden 渠道不得写入 staging**
- `risk_blocked=true` 时阻断
- `customer_type` 必须在枚举范围内
- 必须提供 `source_evidence`, 每条须包含 `evidence_text` 和一致的 `source_url`
- **所有联系方式必须在原始公开文本中出现** (反编造校验)

分级服务 (`llm_lead_grading.py`) 硬规则:
- Invalid/Watch → `touch_queue_allowed=false`, `queue_status=NOT_ELIGIBLE`
- A 级 → `touch_queue_allowed=false`, 不自动触达
- C 级 → `requires_compliance_review=true`, 必须人工合规审核
- High/Forbidden 渠道 → `queue_status=BLOCKED`
- 缺少证据/联系方式 → 降级处理
- `do_not_contact` → 完全阻断

### 5.6 接入真实 LLM Provider

#### 方案 A: Anthropic Claude (推荐)

```bash
# .env 追加
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-api03-xxxxx
LLM_DEFAULT_MODEL=claude-sonnet-4-6
```

调用示例 (在 Service 或外部脚本中):
```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-api03-xxxxx")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    messages=[
        {"role": "user", "content": extraction_prompt + public_text}
    ],
)

llm_output_json = json.loads(response.content[0].text)
# 然后调用 POST /api/llm-lead-extraction/extract
# body: { "candidate_url_id": "...", "llm_output_json": llm_output_json }
```

#### 方案 B: OpenAI 兼容接口

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxxxx",
    base_url="https://api.openai.com/v1"  # 或兼容端点
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    response_format={"type": "json_object"},
)

llm_output_json = json.loads(response.choices[0].message.content)
```

#### 方案 C: 国内兼容接口 (DeepSeek / 通义千问 / 智谱)

```python
# 以 DeepSeek 为例
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxxxx",
    base_url="https://api.deepseek.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    response_format={"type": "json_object"},
)
```

### 5.7 Token 用量与费用控制

系统通过 `AIAuditLog` 表全量记录每次 LLM 调用:

```sql
-- 查看总费用
SELECT
    task_type,
    model_name,
    COUNT(*) as call_count,
    SUM(total_tokens) as total_tokens,
    SUM(cost_amount) as total_cost,
    SUM(CASE WHEN risk_blocked THEN 1 ELSE 0 END) as blocked_count
FROM ai_audit_logs
GROUP BY task_type, model_name;

-- 查看每日用量
SELECT
    DATE(executed_at) as date,
    task_type,
    COUNT(*) as calls,
    SUM(total_tokens) as tokens,
    SUM(cost_amount) as cost
FROM ai_audit_logs
GROUP BY DATE(executed_at), task_type
ORDER BY date DESC;
```

### 5.8 RAG 知识库配置

知识库使用 PostgreSQL pgvector 扩展, 通过 `KnowledgeCollection` + `KnowledgeItem` + `KnowledgeEmbedding` 三张表实现:

```
KnowledgeCollection (知识集合)
    └── KnowledgeItem (知识条目: title, body, language, country)
        └── KnowledgeEmbedding (向量: embedding_model, embedding Vector(1536))
```

预定义知识集合:

| 集合名称 | 用途 | 接入任务 |
|---------|------|---------|
| `keyword_library` | 搜索关键词库 | LEAD_EXTRACTION |
| `channel_sop` | 渠道标准操作流程 | LEAD_EXTRACTION, LEAD_GRADING |
| `compliance_rules` | 合规规则集 | LEAD_GRADING, OUTREACH_DRAFT |
| `failed_cases` | 失败案例库 (可转 RAG) | LEAD_GRADING |
| `faq` | 常见问题 | OUTREACH_DRAFT |
| `script_template` | 话术模板 | OUTREACH_DRAFT |

Embedding 模型: 默认 1536 维 (适配 OpenAI text-embedding-3-small 或 Anthropic Voyage)

### 5.9 渠道风险与 LLM 调用关系

| 风险等级 | 采集允许 | AI 处理允许 | LLM 可调用 | 允许触达 |
|---------|---------|------------|-----------|---------|
| Low | 是 | 是 | 是 | 仅人工 |
| Medium | 是 | 是 | 是 | 仅人工 |
| High | 小样本 | 仅政策研究 | 阻断 | 禁止 |
| Forbidden | 禁止 | 禁止 | 阻断 | 禁止 |

### 5.10 第二阶段 LLM Agent 运行说明

第二阶段已从 P1 的“外部 LLM 输出后入库”推进到后端 `LLMClient` 直接调用 OpenAI-compatible `/chat/completions` 的模式。当前默认 Provider 为 `deepseek`，真实可用性以 `/llm-health` 为准。

必须先确认：

```bash
curl -sS http://127.0.0.1:8000/llm-health
```

只有返回以下字段均为 `true`，才可认定真实外部 LLM 可用：

```json
{
  "base_url_configured": true,
  "api_key_configured": true,
  "configuration_complete": true
}
```

当前第二阶段核心 Agent：

| Agent | 入口 | 写入表 | 审计表 | 说明 |
|---|---|---|---|---|
| SOURCE_DISCOVERY | `POST /agent-tasks/source-discovery/run` | `lead_source_candidates` | `agent_task_runs` | 自动发现线索来源候选，默认按 schema 校验、去重和风险规则入库 |
| LEAD_EXTRACTION | `POST /agent-tasks/lead-extraction/from-sources/run` | `staging_leads` | `agent_task_runs`、`ai_audit_logs` | 从 approved 来源候选池消费来源，执行抽取和分级 |
| Retry/Scheduler | `AgentSchedulerService` | `agent_task_runs` | `agent_task_runs` | 处理技术失败重试、超时恢复和定时运行 |

SOURCE_DISCOVERY 手动启动示例：

```bash
curl -sS -X POST http://127.0.0.1:8000/agent-tasks/source-discovery/run \
  -H 'Content-Type: application/json' \
  -d '{
    "country": "Russia",
    "cities": ["Moscow"],
    "channel_strategy": "Low/Medium公开官网、公开目录、地图公开结果优先；High仅进入人工复核，不自动抽取；Forbidden禁止。",
    "keywords": ["автосалон", "used cars", "import cars"],
    "limit": 20
  }'
```

LEAD_EXTRACTION 手动启动示例：

```bash
curl -sS -X POST http://127.0.0.1:8000/agent-tasks/lead-extraction/from-sources/run \
  -H 'Content-Type: application/json' \
  -d '{
    "limit": 20,
    "country": "Russia",
    "city": "Moscow",
    "trigger_source": "manual_api"
  }'
```

运行核查 SQL：

```sql
select id, task_type, status, trigger_source, error_message, created_at
from agent_task_runs
order by created_at desc
limit 20;

select id, country, city, channel_name, risk_level, review_status, approved_for_extraction, extraction_status, source_url
from lead_source_candidates
order by created_at desc
limit 20;

select id, customer_name, recommended_grade, queue_status, source_url, created_at
from staging_leads
order by created_at desc
limit 20;

select id, task_type, model_name, prompt_version, created_at
from ai_audit_logs
order by created_at desc
limit 20;
```

### 5.11 第二阶段 APScheduler 与 Redis Lock

第二阶段已实现 `AgentSchedulerService` 的任务注册和 Redis lock：

| Job ID | 间隔 | 目标 |
|---|---:|---|
| `source_discovery_hourly` | 3600 秒 | 周期性来源发现 |
| `lead_extraction_interval` | 900 秒 | 周期性从已审核来源创建抽取任务 |
| `retry_failed_tasks` | 300 秒 | 技术失败重试和超时恢复 |

启用前必须满足：

- `REDIS_URL` 已配置并可 `PING`。
- `/llm-health.configuration_complete=true`。
- 已确认调度 job 绑定真实 handler，而不是 placeholder。
- 移动端来源审核和后台看板可用。
- 风险暂停机制已明确到负责人。

配置开关：

```bash
AGENT_SCHEDULER_ENABLED=true
AGENT_SCHEDULER_LOCK_TTL_SECONDS=300
```

重要限制：当前默认 handler 返回 `not_implemented`。若未在应用启动处注入真实 handler，不得把 APScheduler 作为已可生产自动运行的能力。

---

## 6. apps/admin 部署 (Vue3 管理后台)

### 6.1 项目结构

```
apps/admin/
├── src/          # Vue3 源码
├── package.json  # @xagent/admin, Vue 3.5.0
└── vite.config.ts
```

### 6.2 部署步骤

```bash
cd apps/admin

# 安装依赖
npm install

# 开发模式
npm run dev    # → http://0.0.0.0:5174

# 生产构建
npm run build  # → dist/ 静态文件
```

### 6.3 Nginx 部署 (生产)

```nginx
server {
    listen 80;
    server_name admin.xagent.example.com;

    root /path/to/apps/admin/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 7. apps/mobile 部署 (uni-app H5)

### 7.1 项目结构

```
apps/mobile/
├── src/          # uni-app Vue3 源码
├── package.json  # uni-app 3.0 alpha, Vue 3.4.21
└── vite.config.ts
```

### 7.2 部署步骤

```bash
cd apps/mobile

# 安装依赖
npm install

# 开发模式 (H5)
npm run dev:h5   # → http://0.0.0.0:5176

# 生产构建
npm run build:h5 # → dist/build/h5/
```

### 7.3 Nginx 部署

```nginx
server {
    listen 80;
    server_name m.xagent.example.com;

    root /path/to/apps/mobile/dist/build/h5;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
    }
}
```

---

## 8. 数据库初始化与迁移

### 8.1 Alembic 配置

```bash
cd apps/api

# 配置 alembic.ini 中的数据库连接
# sqlalchemy.url = postgresql+psycopg://xagent:password@localhost:5432/xagent

# 查看当前状态
alembic current

# 执行所有待执行的迁移
alembic upgrade head

# 回滚一步
alembic downgrade -1

# 生成新迁移 (修改 models 后)
alembic revision --autogenerate -m "描述"
```

### 8.2 数据库表清单 (当前迁移共 35 张表)

当前表清单以 `apps/api/app/models` 中的 SQLAlchemy ORM 模型和 `apps/api/alembic/versions` 中的 Alembic 迁移为准。其中 33 张为业务运行表，2 张为第一阶段数据层说明/映射表。

#### 8.2.1 客户、线索与触达

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `customers` | 正式客户主表，承载人工复核后进入客服/销售承接的客户。 | name, country, city, customer_type, grade, status, owner, owner_team, do_not_contact |
| `contact_methods` | 正式客户联系方式，记录邮箱、电话、WhatsApp、Telegram、官网表单等公开可验证触达方式。 | customer_id, method_type, value, source_url, evidence_note, is_primary, is_verified |
| `lead_sources` | 正式客户来源证据，保存平台、来源 URL、风险等级和采集证据。 | customer_id, platform, source_url, evidence_note, evidence_excerpt, channel_risk_level |
| `staging_leads` | AI 抽取后的暂存线索池，进入正式客户前需要人工审核、去重和合规判断。 | candidate_url_id, customer_name, country, city, customer_type, contacts_json, recommended_grade, review_status, queue_status, dedupe_key |
| `lead_source_candidates` | Source Discovery Agent 发现的候选来源池，审核通过后才允许进入抽取。 | source_url, normalized_domain, platform, channel_name, country, city, risk_level, review_status, approved_for_extraction, extraction_status, dedupe_key |
| `lead_enrichment_results` | Deep Enrichment Agent 或人工补全的线索增强结果。 | staging_lead_id, enrichment_type, triggered_by, status, input_snapshot_json, output_json, evidence_links, confidence_score, missing_fields, recommended_action |
| `lead_enrichment_field_candidates` | 线索增强产生的字段级候选值，支持逐字段人工接受/拒绝。 | enrichment_result_id, staging_lead_id, field_name, candidate_value, source_type, source_url, evidence_note, confidence_score, review_status |
| `lead_cleanup_runs` | Lead Cleanup Agent 的清洗批次记录，用于追踪一次去重/合并/无效识别任务。 | trigger_source, status, input_snapshot_json, output_summary_json, llm_provider, prompt_template_id, token_usage_json |
| `lead_cleanup_suggestions` | 清洗批次下的具体建议，如重复线索、无效线索、字段冲突或待合并项。 | cleanup_run_id, staging_lead_id, suggestion_type, target_lead_id, reason, evidence_json, review_status, executed_at |
| `customer_vehicle_intents` | 正式客户的车辆采购意向，记录品牌、车型、预算、数量、交付地区和关注点。 | customer_id, brand, model, year_range, quantity, budget_range, delivery_country, concerns, source_type, status |
| `customer_followups` | 客户跟进记录，沉淀客服/销售动作、客户反馈、下一步计划和合规触发。 | customer_id, owner_id, team, followup_type, content, customer_feedback, next_action, next_followup_at, triggered_dnc, triggered_compliance_review |
| `outreach_records` | 人工触达记录，保存发送渠道、话术版本、发送人、负责人、回复摘要和勿扰触发。 | customer_id, channel, status, script_version, sent_by, owner, sent_at, response_summary, next_action, triggers_do_not_contact |
| `compliance_reviews` | C 级报价、合同和高风险动作的人工合规审核记录。 | customer_id, review_type, status, reason, risk_note, reviewer, reviewed_at |

#### 8.2.2 采集、渠道与风险

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `channel_risk_rules` | 渠道风险规则登记表，定义每个渠道的风险等级、允许动作、禁止动作和政策来源。 | channel_name, channel_type, risk_level, collection_allowed, ai_processing_allowed, allowed_actions, forbidden_actions, policy_source_url, updated_by |
| `channel_plans` | 渠道采集计划，控制国家/城市/渠道维度的关键词、每日 URL 限额和线索限额。 | country, city, channel_name, channel_type, risk_level, source_usage_type, keywords, daily_url_limit, daily_lead_limit, status, owner |
| `collection_tasks` | 原始采集任务记录，描述某次渠道发现或采样任务的风险边界和执行状态。 | plan_id, task_type, channel_name, risk_level, source_usage_type, max_sample_size, allowed_actions, forbidden_actions, status |
| `candidate_urls` | 原始候选 URL 队列，记录 URL 哈希、来源平台、风险等级、是否需要二次验证和队列资格。 | task_id, url, url_hash, source_platform, source_risk_level, source_usage_type, requires_secondary_verification, queue_eligible, status |
| `page_snapshots` | 公开页面读取快照，保存页面标题、文本摘要、证据说明、读取状态和政策备注。 | candidate_url_id, page_title, text_excerpt, evidence_note, read_status, captured_at, robots_or_policy_note |
| `risk_events` | 风险事件日志，用于记录阻断、暂停建议、风险等级和人工解决状态。 | channel_plan_id, task_id, agent_name, action, channel, risk_level, event_type, severity, resolution_status, pause_suggested, resolution_note |
| `failed_cases` | 失败案例库，保存抓取失败、schema 错误、证据缺失、风险阻断、重复和疑似编造等案例。 | case_type, source_url, failure_reason, evidence_note, related_task_type, related_object_type, model_name, prompt_version, usable_for_rag, touch_queue_allowed |

#### 8.2.3 车辆、匹配、知识与模板

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `inventory_items` | 轻量车源/报价表，维护品牌、车型、年份、里程、报价、配置、媒体和有效期。 | brand, model, year, mileage_km, vehicle_type, quoted_price, currency, quote_status, export_ready, configuration, media_urls, valid_until |
| `lead_inventory_matches` | 客户与车源的推荐匹配结果，保存匹配分数、推荐理由、风险提示和销售决策。 | customer_id, inventory_item_id, score, recommendation_reason, risk_tips, decision, decision_owner, decision_note |
| `knowledge_collections` | RAG 知识集合，如关键词库、渠道 SOP、合规规则、FAQ、失败案例等。 | name, description, status, review_status, version |
| `knowledge_items` | 知识条目正文，隶属于知识集合，支持国家、语言、版本和审核状态。 | collection_id, title, body, language, country, status, review_status, source_ref, version |
| `knowledge_embeddings` | 知识条目的 pgvector 向量索引表，用于语义检索和 RAG 上下文召回。 | item_id, embedding_model, embedding, embedding_status |
| `script_templates` | 触达话术模板库，保存中文内部话术、俄语客户话术、禁用承诺和审核状态。 | name, script_type, applicable_grades, applicable_channels, chinese_internal_text, russian_customer_text, forbidden_promises, review_status, version |
| `llm_prompt_templates` | LLM Prompt 模板配置表，支持按任务类型、Provider、模型、版本和默认状态管理提示词。 | name, task_type, provider, model, system_prompt, user_prompt_template, output_schema_json, version, status, is_default |

#### 8.2.4 审计、Agent、同步与成本

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `ai_audit_logs` | AI 调用审计日志，全量记录输入、输出、模型、Prompt 版本、Token、费用和风险阻断结果。 | customer_id, task_type, model_name, prompt_version, channel_name, source_url, source_urls, input_payload, output_payload, output_json, total_tokens, cost_amount, risk_blocked |
| `agent_task_runs` | 第二阶段 Agent 任务运行审计表，覆盖任务类型、状态、输入输出摘要、LLM 配置、Token、延迟和重试次数。 | task_type, status, trigger_source, input_json, output_summary_json, llm_provider, llm_model, prompt_template_id, token_usage_json, latency_ms, retry_count |
| `agent_run_logs` | 第一阶段 Agent 执行日志，用于记录 agent_name、动作、输入输出引用和执行结果。 | task_id, agent_name, action, input_ref, output_ref, result, error_message, started_at, finished_at |
| `review_logs` | 人工/Agent 复核日志，记录复核人、动作、输入输出引用和结论。 | task_id, agent_name, action, reviewer, input_ref, output_ref, result, error_message |
| `sync_logs` | 飞书或其他外部系统同步日志，记录对象、成功/失败数量、错误摘要和元数据。 | source_name, object_name, status, success_count, failure_count, error_summary, metadata_json, started_at, finished_at |
| `roi_cost_entries` | ROI 成本记录，保存 LLM、人工、渠道等成本类型、金额、币种、工时和渠道归属。 | cost_type, amount, currency, labor_hours, hourly_rate, channel_name, notes, occurred_at |

#### 8.2.5 数据层说明表

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `phase1_data_layers` | 第一阶段 raw/staging/core/audit/knowledge 数据层基线说明表，记录每层用途、允许表和准入门槛。 | layer_name, layer_order, purpose, allowed_tables, entry_gate |
| `phase1_data_layer_table_map` | 第一阶段业务表到数据层的映射表，记录表名、层级、表角色、规划 Story 和备注。 | table_name, layer_name, table_role, planned_story, notes |

### 8.3 核心枚举值

```
CustomerGrade:       A | B | C | Invalid | Watch
CustomerStatus:      NEW | NEEDS_ENRICHMENT | PENDING_REVIEW | READY_FOR_CUSTOMER_SERVICE | ... | DO_NOT_CONTACT
CustomerType:        LOCAL_DEALER_SECONDARY_DEALER | PERSONAL_BUYER | KOL_AUTO_BLOGGER | UNKNOWN | NON_TARGET
ChannelRiskLevel:     Low | Medium | High | Forbidden
ContactMethodType:   EMAIL | PHONE | WHATSAPP | TELEGRAM | VKONTAKTE | ODNOKLASSNIKI | TIKTOK | MAX | WEBSITE | WEBSITE_FORM | OTHER
SourcePlatform:       OFFICIAL_WEBSITE | PUBLIC_DIRECTORY | SEARCH_ENGINE | GOOGLE_MAPS | YANDEX_MAPS | YOUTUBE | DROM | OTHER
AITaskType:           LEAD_EXTRACTION | LEAD_GRADING | OUTREACH_DRAFT | INVENTORY_MATCHING | RISK_BLOCK
```

---

## 9. Seed 数据导入

```bash
cd apps/api

# 运行 seed 脚本
python -m scripts.seed_data

# 或分步执行
python -m scripts.seed_channel_risk_rules
python -m scripts.seed_customers
python -m scripts.seed_inventory
python -m scripts.seed_scripts
python -m scripts.seed_knowledge
```

Seed 数据包含:
- **20 条渠道风险规则** — 覆盖 Low/Medium/High/Forbidden 四级
- **20 条渠道采集计划** — 对应 20 个渠道
- **20 条客户线索** — A/B/C/Invalid/Watch 分布
- **50+ 条联系方式** — 多渠道 (email/phone/WhatsApp/Telegram)
- **20 条来源记录** — 多平台
- **20 条车源报价** — 日系/德系/中国品牌
- **20 条触达记录** — 多状态
- **20 条话术模板** — 初次触达/FAQ/拒绝路径
- **6 个知识集合 + 知识条目** — RAG 所需

详见 `apps/api/scripts/seed_data.py`。

---

## 10. 环境变量清单

| 变量名 | 必填 | 默认值 | 说明 |
|-------|------|-------|------|
| `DATABASE_URL` | 是 | `postgresql+asyncpg://vehicle_leads:vehicle_leads@localhost:5432/vehicle_leads` | PostgreSQL 连接串 |
| `REDIS_URL` | 否 | `None` | Redis 连接串 |
| `FEISHU_APP_ID` | 否 | `None` | 飞书 App ID |
| `FEISHU_APP_SECRET` | 否 | `None` | 飞书 App Secret |
| `FEISHU_BITABLE_APP_TOKEN` | 否 | `None` | 飞书多维表格 Token |
| `CORS_ORIGINS` | 否 | `http://localhost:5176,...` | 跨域白名单 |
| `LLM_PROVIDER` | 否 | - | LLM 提供商 (anthropic/openai/...) |
| `LLM_API_KEY` | 否 | - | LLM API Key |
| `LLM_DEFAULT_MODEL` | 否 | - | 默认模型 |
| `LLM_EXTRACTION_MODEL` | 否 | - | 抽取任务专用模型 |
| `LLM_GRADING_MODEL` | 否 | - | 分级任务专用模型 |

---

## 11. 日常运维操作

### 11.1 每日操作流程

```
1. 飞书数据同步     → POST /api/sync/sync
2. AI 线索抽取      → POST /api/llm-lead-extraction/extract (批量)
3. AI 线索分级      → POST /api/llm-lead-grading/grade (批量)
4. 人工复核 staging  → GET /api/staging-leads → PUT approve/reject
5. 合规审核 (C 级)  → GET /api/compliance → PUT approve/reject
6. 触达跟进         → GET /api/customers/outreach-candidates
```

### 11.2 健康检查

```bash
curl http://localhost:8000/health
```

### 11.3 日志查看

```bash
# API 日志
journalctl -u xagent-api -f

# 数据库连接数
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='xagent';"
```

### 11.4 第二阶段小范围运行日常检查

每日运行前：

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/llm-health
redis-cli -u "$REDIS_URL" ping
```

每日运行后：

```sql
select task_type, status, count(*)
from agent_task_runs
where created_at >= now() - interval '1 day'
group by task_type, status
order by task_type, status;

select risk_level, review_status, approved_for_extraction, count(*)
from lead_source_candidates
where created_at >= now() - interval '1 day'
group by risk_level, review_status, approved_for_extraction
order by risk_level, review_status;

select recommended_grade, queue_status, count(*)
from staging_leads
where created_at >= now() - interval '1 day'
group by recommended_grade, queue_status
order by recommended_grade, queue_status;
```

暂停条件：

- B 级线索比例持续低于 20%。
- 触达几乎无回复。
- 出现投诉、封禁、违规风险或平台警告。
- 销售/客服拒绝承接线索。
- 贸易路径、付款、物流或清关路径不可行。
- 任一流程尝试自动社交私信、自动加好友、登录后批量采集或反爬规避。

暂停动作：

1. 设置 `AGENT_SCHEDULER_ENABLED=false` 并重启 API。
2. 暂停相关渠道计划。
3. 保留并归档 `agent_task_runs`、`lead_source_candidates`、`staging_leads`、`ai_audit_logs`。
4. 合规负责人完成复盘后，再以人工小样本恢复。

---

## 12. 合规红线与安全约束

以下规则硬编码在 Service 层, 不可通过配置关闭:

| 红线 | 实现 | 位置 |
|------|------|------|
| 不得自动发送社交消息 | `auto_send_enabled=false` | `outreach_draft.py` |
| 不得自动加好友/关注 | `forbidden_actions` 含 friend_request | `channel_risk.py` |
| 不得登录采集 | `forbidden_actions` 含 login | `channel_risk.py` |
| 不得绕过反爬 | `forbidden_actions` 含 scrape | `channel_risk.py` |
| 不得承诺价格/物流/清关/付款 | `FORBIDDEN_COMMITMENTS` 检测 | `outreach_draft.py` |
| 不得编造联系方式 | contacts 必须在原文中存在 | `llm_lead_extraction.py` |
| C 级必须合规审核 | `requires_compliance_review=true` | `llm_lead_grading.py` |
| High/Forbidden 阻断写入 | 校验失败抛异常 | `llm_lead_extraction.py` |
| 全量审计日志 | 每次 LLM 调用写入 AIAuditLog | `audit_risk.py` |
