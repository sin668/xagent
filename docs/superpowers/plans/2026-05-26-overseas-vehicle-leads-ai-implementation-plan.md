# Overseas Vehicle Leads AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a Russia-focused AI-assisted overseas vehicle lead workflow, then productize the validated loop into a lightweight CRM.

**Architecture:** The project runs in two phases. The 2-week PoC uses Feishu tables, controlled public-source research, AI-assisted cleaning, human review, and manual outreach. The 4-week MVP adds a Vue3/uni-app/FastAPI/PostgreSQL lightweight CRM with Feishu one-way sync, AI recommendation panels, audit logs, SLA tracking, and compliance guardrails.

**Tech Stack:** Feishu tables, CSV, Python scripts, LLM API, Vue3, uni-app(Vue3), FastAPI, PostgreSQL, SQLAlchemy or SQLModel, Alembic, Celery/RQ/Arq, Feishu API.

---

## Scope Check

This plan intentionally avoids a full SaaS build. It implements the approved path: **2-week PoC + 4-week MVP**.

Non-goals for this plan:

- No automatic social-platform private messaging.
- No automated friend requests, group joins, or login-required platform scraping.
- No anti-bot bypass, account-pool evasion, or non-public data extraction.
- No multi-country expansion before the Russia PoC passes.
- No complex black-box lead scoring model in phase one.

The current workspace is not a git repository. Commit steps are written as recommended actions for the future implementation repository; if the implementation still happens in this non-git directory, skip commit commands and record completed tasks in the plan checkboxes.

## File Structure

Create these files during implementation:

```text
docs/
  poc/
    feishu-table-schemas.md
    channel-risk-register.md
    keyword-library-ru.md
    outreach-sop.md
    lead-review-sop.md
    poc-daily-log.md
    poc-retrospective.md
  crm/
    mvp-requirements.md
    data-dictionary.md
    api-contract.md
    qa-checklist.md
data/
  templates/
    leads.csv
    channels.csv
    inventory.csv
    outreach_records.csv
    scripts.csv
    failed_cases.csv
    faq_objections.csv
  samples/
    sample-leads-20.csv
    sample-inventory.csv
prompts/
  lead-extraction.ru.md
  lead-classification.md
  outreach-draft.ru.md
  compliance-risk-check.md
scripts/
  poc/
    validate_leads_csv.py
    dedupe_leads.py
    score_lead_rules.py
    export_poc_metrics.py
apps/
  api/
    app/main.py
    app/core/config.py
    app/db/session.py
    app/models/lead.py
    app/models/source.py
    app/models/contact.py
    app/models/outreach.py
    app/models/audit_log.py
    app/models/compliance.py
    app/api/routes/leads.py
    app/api/routes/sync.py
    app/api/routes/dashboard.py
    app/services/feishu_sync.py
    app/services/ai_audit.py
    app/services/lead_rules.py
    tests/test_lead_rules.py
    tests/test_feishu_sync_mapping.py
  web/
    src/views/LeadBoard.vue
    src/views/LeadDetail.vue
    src/views/Dashboard.vue
    src/components/AiRecommendationPanel.vue
    src/components/ComplianceBadge.vue
  mobile/
    pages/leads/index.vue
    pages/leads/detail.vue
```

## Phase 0: Startup Inputs

### Task 0: Confirm Operating Inputs

**Files:**
- Create: `docs/poc/poc-daily-log.md`

- [ ] **Step 1: Create the PoC daily log**

Write this file:

```markdown
# PoC Daily Log

## Operating Inputs

- PoC market: Russia
- Customer target: local auto dealers / secondary dealers
- Vehicle focus: used, nearly-new, inventory vehicles
- Primary metric: B-grade qualified leads
- Secondary metric: outreach replies
- Observation metric: sales opportunities

## Role Owners

| Responsibility | Owner | Backup | Daily time budget |
|---|---|---|---|
| Business decision | Business owner | Export sales lead | 30 min |
| Lead operations | Lead ops owner | Data reviewer | 2 h |
| AI/Agent operation | AI operator | Technical lead | 2 h |
| Customer service | CS lead | CS member | 1 h |
| Export sales | Sales lead | Sales member | 1 h |
| Compliance/risk | Compliance owner | Business owner | 30 min |

## Daily Log

| Date | Work completed | Leads added | B-grade leads | Outreach sent | Replies | Risks | Decisions |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-26 | Kickoff | 0 | 0 | 0 | 0 | None | Start PoC setup |
```

- [ ] **Step 2: Verify the file exists**

Run:

```bash
test -f docs/poc/poc-daily-log.md && echo "daily log ready"
```

Expected output:

```text
daily log ready
```

- [ ] **Step 3: Record owner names**

Replace each `Owner` and `Backup` cell with real names before daily execution starts. If a role is shared, write both names in the cell.

## Phase 1: 2-Week PoC

### Task 1: Build the Feishu Table Schemas

**Files:**
- Create: `docs/poc/feishu-table-schemas.md`
- Create: `data/templates/leads.csv`
- Create: `data/templates/channels.csv`
- Create: `data/templates/inventory.csv`
- Create: `data/templates/outreach_records.csv`
- Create: `data/templates/scripts.csv`

- [ ] **Step 1: Write the schema document**

Create `docs/poc/feishu-table-schemas.md` with:

```markdown
# Feishu Table Schemas

## 1. Customer Leads

Fields:

- lead_id
- customer_name
- country
- city
- customer_type
- lead_grade
- lead_status
- primary_contact_type
- primary_contact_value
- source_count
- primary_source_url
- source_platform
- business_activity
- scale_signal
- import_used_relevance
- evidence_note
- ai_recommendation
- ai_missing_fields
- ai_risk_note
- assigned_team
- assigned_owner
- first_assigned_at
- first_followed_at
- next_action
- do_not_contact
- created_at
- updated_at

Allowed lead_grade values: A, B, C, Invalid, Watch.
Allowed lead_status values: New, Need Enrichment, Need Review, Ready for CS, CS In Progress, Ready for Sales, Sales In Progress, Invalid, Watch, Do Not Contact.

## 2. Channel Sources

Fields:

- channel_id
- country
- platform
- source_type
- search_keyword
- source_url
- risk_level
- allowed_actions
- prohibited_actions
- policy_source_url
- notes
- active

Allowed risk_level values: Low, Medium, High, Forbidden.

## 3. Vehicle Inventory

Fields:

- inventory_id
- brand
- model
- year
- mileage_km
- condition
- configuration
- price_currency
- price_amount
- export_ready
- media_url
- valid_until
- notes

## 4. Outreach Records

Fields:

- outreach_id
- lead_id
- channel
- script_id
- sender
- sent_at
- reply_status
- reply_summary
- next_action
- do_not_contact_marked

Allowed reply_status values: Not Sent, Sent, Replied, Rejected, No Response, Wrong Contact.

## 5. Script Library

Fields:

- script_id
- language
- scenario
- channel
- customer_type
- script_text
- risk_note
- approved_by
- approved_at
- active
```

- [ ] **Step 2: Create CSV templates**

Create CSV files with these exact header rows:

```csv
lead_id,customer_name,country,city,customer_type,lead_grade,lead_status,primary_contact_type,primary_contact_value,source_count,primary_source_url,source_platform,business_activity,scale_signal,import_used_relevance,evidence_note,ai_recommendation,ai_missing_fields,ai_risk_note,assigned_team,assigned_owner,first_assigned_at,first_followed_at,next_action,do_not_contact,created_at,updated_at
```

```csv
channel_id,country,platform,source_type,search_keyword,source_url,risk_level,allowed_actions,prohibited_actions,policy_source_url,notes,active
```

```csv
inventory_id,brand,model,year,mileage_km,condition,configuration,price_currency,price_amount,export_ready,media_url,valid_until,notes
```

```csv
outreach_id,lead_id,channel,script_id,sender,sent_at,reply_status,reply_summary,next_action,do_not_contact_marked
```

```csv
script_id,language,scenario,channel,customer_type,script_text,risk_note,approved_by,approved_at,active
```

- [ ] **Step 3: Validate templates are non-empty**

Run:

```bash
wc -l data/templates/*.csv
```

Expected: each template reports at least `1` line.

### Task 2: Build the Channel Risk Register

**Files:**
- Create: `docs/poc/channel-risk-register.md`

- [ ] **Step 1: Create the risk register**

Write:

```markdown
# Channel Risk Register

| Channel | Initial risk | Allowed in PoC | Prohibited in PoC | Evidence/source |
|---|---|---|---|---|
| Company websites | Low | Public page review, public contact extraction, manual outreach | Password-protected extraction | Public website terms per site |
| Public directories | Low | Public listing review, manual verification | Bulk scraping without terms review | Directory terms per site |
| Search engines | Low | Search result discovery, manual review | Automated high-volume scraping | Search engine and robots guidance |
| Google Maps / Places | Medium | Manual review or official API under storage rules | Scraping, unrestricted storage of Places data | https://cloud.google.com/maps-platform/terms |
| YouTube | Medium | Manual review, official API where permitted | Scraping, automated commenting, automated messaging | https://tv.youtube.com/tv/terms |
| Telegram public channels | Medium | Manual channel review, public description capture | Auto-join, auto-DM, spam messaging | https://telegram.org/tos/eu |
| X | High | Policy research only during PoC | Non-API scraping, automated following, automated DM | https://docs.x.com/developer-guidelines |
| Facebook / Instagram | High | Policy research only during PoC | Automated data collection, auto-DM | https://www.facebook.com/legal/automated_data_collection_terms |
| Avito | High | Policy research and manual sample review | Automated collection until official terms reviewed | Official terms to be reviewed before use |
| VK | High | Policy research and manual sample review | Automated collection until official terms reviewed | Official terms/API rules to be reviewed before use |
| Auto.ru | High | Policy research and manual sample review | Automated collection until official terms reviewed | https://yandex.ru/legal/autoru_terms_of_service/ru/index.html |
| Drom | High | Manual sample review | Automated collection until license reviewed | https://www.drom.ru/commerce/license/ |
```

- [ ] **Step 2: Add the execution rule**

Append:

```markdown
## Execution Rule

An AI or Agent workflow may run only against channels marked Low or Medium, and only for the allowed PoC actions listed above. High-risk channels are research-only until the compliance owner approves a written channel SOP.
```

### Task 3: Build the Russian Keyword Library

**Files:**
- Create: `docs/poc/keyword-library-ru.md`

- [ ] **Step 1: Create seed keywords**

Write:

```markdown
# Russian Market Keyword Library

## Customer Keywords

| Intent | Russian | English | Chinese |
|---|---|---|---|
| car dealer | автодилер | auto dealer | 汽车经销商 |
| used car dealer | дилер подержанных автомобилей | used car dealer | 二手车商 |
| car showroom | автосалон | car showroom | 汽车展厅/车行 |
| imported cars | импортные автомобили | imported cars | 进口车 |
| wholesale cars | автомобили оптом | wholesale cars | 批发车源 |
| Chinese cars | китайские автомобили | Chinese cars | 中国车 |

## Vehicle Keywords

| Intent | Russian | English | Chinese |
|---|---|---|---|
| used cars | подержанные автомобили | used cars | 二手车 |
| nearly new cars | почти новые автомобили | nearly new cars | 准新车 |
| stock vehicles | автомобили в наличии | vehicles in stock | 库存车 |
| car import | импорт автомобилей | car import | 汽车进口 |

## Region Keywords

| City | Russian | English |
|---|---|---|
| Moscow | Москва | Moscow |
| Saint Petersburg | Санкт-Петербург | Saint Petersburg |
| Vladivostok | Владивосток | Vladivostok |
| Novosibirsk | Новосибирск | Novosibirsk |
| Kazan | Казань | Kazan |

## Exclusion Keywords

| Russian | English | Chinese |
|---|---|---|
| ремонт | repair | 维修 |
| запчасти | spare parts | 配件 |
| страховка | insurance | 保险 |
| кредит | loan | 贷款 |
| вакансии | jobs | 招聘 |
```

- [ ] **Step 2: Create first query combinations**

Append:

```markdown
## First Query Combinations

- автосалон китайские автомобили Москва
- дилер подержанных автомобилей импортные автомобили Москва
- автомобили оптом китайские автомобили Россия
- автодилер автомобили в наличии Владивосток
- car dealer Chinese cars Russia
- used car dealer imported cars Moscow
```

### Task 4: Create the AI Prompts

**Files:**
- Create: `prompts/lead-extraction.ru.md`
- Create: `prompts/lead-classification.md`
- Create: `prompts/outreach-draft.ru.md`
- Create: `prompts/compliance-risk-check.md`

- [ ] **Step 1: Create lead extraction prompt**

Write `prompts/lead-extraction.ru.md`:

```markdown
# Lead Extraction Prompt

You extract structured B2B vehicle customer information from public Russian-market source text.

Return JSON only with these keys:

{
  "customer_name": "",
  "country": "Russia",
  "city": "",
  "customer_type": "Dealer | Secondary Dealer | KOL | Personal Buyer | Irrelevant | Unknown",
  "contacts": [{"type": "email | phone | whatsapp | telegram | vk | website | unknown", "value": ""}],
  "business_activity": "High | Medium | Low | Unknown",
  "scale_signal": "Large | Medium | Small | Unknown",
  "import_used_relevance": "Strong | Medium | Weak | Unknown",
  "evidence_note": "",
  "missing_fields": [],
  "risk_note": ""
}

Rules:

- Use only information visible in the provided source text.
- Do not invent contacts, cities, vehicle brands, prices, or import claims.
- If evidence is weak, use Unknown.
- If the source looks like repair, spare parts, insurance, loans, jobs, or media-only content, mark customer_type as Irrelevant or KOL.
```

- [ ] **Step 2: Create classification prompt**

Write `prompts/lead-classification.md`:

```markdown
# Lead Classification Prompt

Classify a lead into A, B, C, Invalid, or Watch.

A-grade requires:
- customer_name
- country or city
- source URL
- customer_type
- at least one contact method

B-grade requires A-grade plus:
- main business or vehicle focus
- evidence of used/import/vehicle relevance
- activity or scale signal
- matching reason for used/nearly-new/inventory vehicles

C-grade requires B-grade plus one of:
- customer replied
- customer asked for price
- customer expressed purchase/import interest
- customer agreed to continue on WhatsApp, Telegram, WeChat, email, or phone
- customer provided vehicle demand

Invalid:
- duplicate with no new evidence
- no contact method after enrichment
- not a vehicle sales/import/customer lead
- prohibited source or high compliance risk

Watch:
- relevant but not ready for outreach
- lacks contact but has useful market signal

Return JSON:
{
  "lead_grade": "",
  "reason": "",
  "next_action": "",
  "handoff_team": "None | Customer Service | Export Sales"
}
```

- [ ] **Step 3: Create outreach draft prompt**

Write `prompts/outreach-draft.ru.md`:

```markdown
# Russian Outreach Draft Prompt

Write a short Russian outreach draft for a vehicle dealer.

Inputs:
- customer type
- source evidence
- vehicle category
- contact channel
- approved FAQ facts

Rules:
- Do not promise final price, delivery time, customs clearance, payment terms, or vehicle availability unless provided in approved facts.
- Do not pressure the customer.
- Include a simple opt-out line for email or web-form outreach.
- Keep it under 90 Russian words.
- End with a low-friction question asking whether they buy used, nearly-new, or inventory vehicles from China.

Return:
{
  "subject": "",
  "message": "",
  "risk_note": ""
}
```

- [ ] **Step 4: Create compliance risk prompt**

Write `prompts/compliance-risk-check.md`:

```markdown
# Compliance Risk Check Prompt

Review the lead, source, and proposed outreach.

Return JSON:
{
  "platform_risk": "Low | Medium | High | Forbidden",
  "data_risk": "Low | Medium | High",
  "trade_risk": "Low | Medium | High | Needs Human Review",
  "message_risk": "Low | Medium | High",
  "required_human_action": "",
  "blocked": true
}

Blocking rules:
- Block if source is non-public or login-only.
- Block if the action requires automated private messaging, friend requests, or group joining.
- Block if the message promises price, customs, logistics, payment, or delivery without approved facts.
- Mark trade_risk as Needs Human Review before any C-grade quote or contract discussion for Russia.
```

### Task 5: Create PoC CSV Validation Scripts

**Files:**
- Create: `scripts/poc/validate_leads_csv.py`
- Create: `scripts/poc/dedupe_leads.py`
- Create: `scripts/poc/score_lead_rules.py`
- Create: `scripts/poc/export_poc_metrics.py`

- [ ] **Step 1: Implement CSV validation**

Write `scripts/poc/validate_leads_csv.py`:

```python
import csv
import sys

REQUIRED = {
    "lead_id",
    "customer_name",
    "country",
    "customer_type",
    "lead_grade",
    "lead_status",
    "primary_source_url",
    "source_platform",
    "created_at",
    "updated_at",
}

def main(path: str) -> int:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            print(f"missing columns: {sorted(missing)}")
            return 1
        errors = []
        for index, row in enumerate(reader, start=2):
            if not row["lead_id"]:
                errors.append(f"line {index}: lead_id is empty")
            if not row["customer_name"]:
                errors.append(f"line {index}: customer_name is empty")
            if row["lead_grade"] not in {"A", "B", "C", "Invalid", "Watch"}:
                errors.append(f"line {index}: invalid lead_grade {row['lead_grade']!r}")
        if errors:
            print("\n".join(errors))
            return 1
        print("leads csv valid")
        return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
```

- [ ] **Step 2: Implement deterministic dedupe**

Write `scripts/poc/dedupe_leads.py`:

```python
import csv
import sys
from collections import defaultdict

def key(row: dict) -> tuple[str, str]:
    name = (row.get("customer_name") or "").strip().lower()
    contact = (row.get("primary_contact_value") or "").strip().lower()
    return name, contact

def main(path: str) -> int:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            groups[key(row)].append(row.get("lead_id", ""))
    duplicates = {k: v for k, v in groups.items() if k != ("", "") and len(v) > 1}
    if not duplicates:
        print("no duplicates found")
        return 0
    for (name, contact), ids in duplicates.items():
        print(f"duplicate: name={name} contact={contact} ids={','.join(ids)}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
```

- [ ] **Step 3: Implement rule scoring**

Write `scripts/poc/score_lead_rules.py`:

```python
def score(row: dict) -> str:
    has_base = all([
        row.get("customer_name"),
        row.get("country") or row.get("city"),
        row.get("customer_type"),
        row.get("primary_contact_value"),
        row.get("primary_source_url"),
    ])
    has_b = all([
        has_base,
        row.get("business_activity") in {"High", "Medium"},
        row.get("import_used_relevance") in {"Strong", "Medium"},
        row.get("evidence_note"),
    ])
    has_c = row.get("lead_status") in {"Ready for Sales", "Sales In Progress"}
    if has_c and has_b:
        return "C"
    if has_b:
        return "B"
    if has_base:
        return "A"
    return "Watch"

if __name__ == "__main__":
    import csv
    import sys
    with open(sys.argv[1], newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            print(f"{row.get('lead_id')},{score(row)}")
```

- [ ] **Step 4: Implement metric export**

Write `scripts/poc/export_poc_metrics.py`:

```python
import csv
import sys
from collections import Counter

def main(path: str) -> int:
    grades = Counter()
    statuses = Counter()
    platforms = Counter()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            grades[row.get("lead_grade") or "Unknown"] += 1
            statuses[row.get("lead_status") or "Unknown"] += 1
            platforms[row.get("source_platform") or "Unknown"] += 1
    print("# PoC Metrics")
    print("\n## Grades")
    for key, value in grades.most_common():
        print(f"- {key}: {value}")
    print("\n## Statuses")
    for key, value in statuses.most_common():
        print(f"- {key}: {value}")
    print("\n## Platforms")
    for key, value in platforms.most_common():
        print(f"- {key}: {value}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
```

- [ ] **Step 5: Run script syntax checks**

Run:

```bash
python3 -m py_compile scripts/poc/validate_leads_csv.py scripts/poc/dedupe_leads.py scripts/poc/score_lead_rules.py scripts/poc/export_poc_metrics.py
```

Expected: no output and exit code `0`.

### Task 6: Execute the First 50-Lead Pilot

**Files:**
- Create: `data/samples/sample-leads-20.csv`
- Modify: `docs/poc/poc-daily-log.md`

- [ ] **Step 1: Collect 50 public-source candidates**

Use only Low or Medium channels from `docs/poc/channel-risk-register.md`. For each candidate, record at least:

```text
customer_name, country, city, customer_type, primary_source_url, source_platform, evidence_note
```

- [ ] **Step 2: Run validation**

Run:

```bash
python3 scripts/poc/validate_leads_csv.py data/samples/sample-leads-20.csv
```

Expected output if the pilot sample is structurally valid:

```text
leads csv valid
```

- [ ] **Step 3: Run dedupe**

Run:

```bash
python3 scripts/poc/dedupe_leads.py data/samples/sample-leads-20.csv
```

Expected output for a clean pilot:

```text
no duplicates found
```

- [ ] **Step 4: Update daily log**

Append one row to `docs/poc/poc-daily-log.md` with collected count, B-grade count, source channels, and any risk notes.

### Task 7: Scale to 100-200 Leads

**Files:**
- Modify: `data/templates/leads.csv` or Feishu Customer Leads table
- Modify: `docs/poc/poc-daily-log.md`

- [ ] **Step 1: Expand only channels that passed the 50-lead pilot**

Add more candidates from the top-performing sources. Stop a channel if 30-50 collected leads produce no B-grade leads.

- [ ] **Step 2: Record every lead source**

Each lead must have a `primary_source_url` and `evidence_note`. If source evidence cannot be recorded, set `lead_status` to `Need Review`.

- [ ] **Step 3: Export daily metrics**

Run:

```bash
python3 scripts/poc/export_poc_metrics.py data/templates/leads.csv > docs/poc/latest-poc-metrics.md
```

Expected: `docs/poc/latest-poc-metrics.md` contains grade, status, and platform counts.

### Task 8: Run Manual Outreach Sample

**Files:**
- Create: `docs/poc/outreach-sop.md`
- Modify: `data/templates/outreach_records.csv`

- [ ] **Step 1: Write outreach SOP**

Write:

```markdown
# Outreach SOP

## Allowed PoC Outreach

- Manual email.
- Manual website form submission.
- Manual WhatsApp/Telegram/VK only when the contact is publicly listed and the compliance owner approves the sample.

## Prohibited PoC Outreach

- Automated social private messages.
- Automated friend requests.
- Automated group joins.
- Re-contacting a customer marked Do Not Contact.
- Sending unapproved pricing, logistics, customs, or payment promises.

## Minimum Message Review

Before sending, verify:

- Lead is B-grade or C-grade.
- Source is Low or approved Medium risk.
- Message uses approved script or FAQ.
- Sender records channel and sent time.
- Customer can reject further contact.
```

- [ ] **Step 2: Select outreach sample**

Select 10-20 B/C-grade leads. Do not include leads from High-risk sources.

- [ ] **Step 3: Record every outreach**

For each message, write one row in `data/templates/outreach_records.csv` with `reply_status` initially set to `Sent`.

- [ ] **Step 4: Mark refusals immediately**

If a customer refuses contact, set `do_not_contact_marked` to `true` and update the lead status to `Do Not Contact`.

### Task 9: Write the PoC Retrospective

**Files:**
- Create: `docs/poc/poc-retrospective.md`

- [ ] **Step 1: Write the retrospective structure**

Use:

```markdown
# Russia Vehicle Lead PoC Retrospective

## Summary Decision

- Decision: Continue to MVP / Repeat PoC / Stop
- Reason:

## Metrics

| Metric | Result | Pass threshold | Pass |
|---|---:|---:|---|
| Sustainable low/medium-risk channels | 0 | 3 | No |
| Total leads | 0 | 100-200 | No |
| B-grade ratio | 0% | 30%-50% | No |
| Manual outreach sample | 0 | 10-20 | No |
| Replies or clear negative feedback | 0 | At least one signal | No |
| Platform complaints or account issues | 0 | 0 | Yes |

## Channel Findings

## Lead Quality Findings

## Outreach Findings

## Compliance Findings

## Team Handoff Findings

## MVP Recommendation
```

- [ ] **Step 2: Fill metrics from Feishu/CSV**

Use `docs/poc/latest-poc-metrics.md` and outreach records.

- [ ] **Step 3: Make a go/no-go recommendation**

Choose exactly one:

```text
Continue to MVP
Repeat PoC with adjusted channels
Stop Russia track and reassess market
```

## Phase 2: 4-Week MVP

### Task 10: Scaffold Backend API

**Files:**
- Create: `apps/api/app/main.py`
- Create: `apps/api/app/core/config.py`
- Create: `apps/api/app/db/session.py`

- [ ] **Step 1: Create FastAPI app**

Write `apps/api/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Vehicle Leads CRM API")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 2: Create config**

Write `apps/api/app/core/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://vehicle_leads:vehicle_leads@localhost:5432/vehicle_leads"
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    llm_model: str = "configured-by-environment"

settings = Settings()
```

- [ ] **Step 3: Create DB session**

Write `apps/api/app/db/session.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Run health endpoint**

Run:

```bash
uvicorn apps.api.app.main:app --reload
```

Expected: `GET /health` returns `{"status":"ok"}`.

### Task 11: Implement Core Database Models

**Files:**
- Create: `apps/api/app/models/lead.py`
- Create: `apps/api/app/models/source.py`
- Create: `apps/api/app/models/contact.py`
- Create: `apps/api/app/models/outreach.py`
- Create: `apps/api/app/models/audit_log.py`
- Create: `apps/api/app/models/compliance.py`

- [ ] **Step 1: Define lead model**

Write `apps/api/app/models/lead.py`:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Boolean, DateTime, String, Text, func

class Base(DeclarativeBase):
    pass

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str] = mapped_column(String(80), default="Russia")
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_type: Mapped[str] = mapped_column(String(80), default="Unknown")
    lead_grade: Mapped[str] = mapped_column(String(20), default="A")
    lead_status: Mapped[str] = mapped_column(String(60), default="New")
    business_activity: Mapped[str] = mapped_column(String(20), default="Unknown")
    scale_signal: Mapped[str] = mapped_column(String(20), default="Unknown")
    import_used_relevance: Mapped[str] = mapped_column(String(20), default="Unknown")
    evidence_note: Mapped[str] = mapped_column(Text, default="")
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_team: Mapped[str | None] = mapped_column(String(80), nullable=True)
    assigned_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: Define related models**

Create models for source, contact, outreach, audit, and compliance with foreign key `lead_id`, timestamp fields, and text notes. Keep each model in its own file and use `Lead` as the parent entity.

- [ ] **Step 3: Add migrations**

Run:

```bash
alembic revision --autogenerate -m "create lead crm core tables"
alembic upgrade head
```

Expected: PostgreSQL contains lead, source, contact, outreach, audit, and compliance tables.

### Task 12: Implement Lead Rules Tests

**Files:**
- Create: `apps/api/app/services/lead_rules.py`
- Create: `apps/api/tests/test_lead_rules.py`

- [ ] **Step 1: Write tests first**

Write `apps/api/tests/test_lead_rules.py`:

```python
from app.services.lead_rules import classify_lead

def test_a_grade_requires_base_fields():
    row = {
        "customer_name": "Moscow Auto",
        "country": "Russia",
        "customer_type": "Dealer",
        "primary_contact_value": "+7 000 000",
        "primary_source_url": "https://example.com",
    }
    assert classify_lead(row)["lead_grade"] == "A"

def test_b_grade_requires_relevance_and_activity():
    row = {
        "customer_name": "Moscow Auto",
        "country": "Russia",
        "customer_type": "Dealer",
        "primary_contact_value": "+7 000 000",
        "primary_source_url": "https://example.com",
        "business_activity": "High",
        "import_used_relevance": "Strong",
        "evidence_note": "Publishes used imported vehicle inventory.",
    }
    assert classify_lead(row)["lead_grade"] == "B"

def test_do_not_contact_blocks_handoff():
    row = {
        "customer_name": "Moscow Auto",
        "country": "Russia",
        "customer_type": "Dealer",
        "primary_contact_value": "+7 000 000",
        "primary_source_url": "https://example.com",
        "do_not_contact": True,
    }
    result = classify_lead(row)
    assert result["lead_grade"] == "Invalid"
    assert result["handoff_team"] == "None"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd apps/api && pytest tests/test_lead_rules.py -v
```

Expected: tests fail because `app.services.lead_rules` does not exist.

- [ ] **Step 3: Implement lead rules**

Write `apps/api/app/services/lead_rules.py`:

```python
def classify_lead(row: dict) -> dict:
    if row.get("do_not_contact"):
        return {"lead_grade": "Invalid", "handoff_team": "None", "reason": "Do not contact"}

    has_base = all([
        row.get("customer_name"),
        row.get("country") or row.get("city"),
        row.get("customer_type"),
        row.get("primary_contact_value"),
        row.get("primary_source_url"),
    ])
    has_b = all([
        has_base,
        row.get("business_activity") in {"High", "Medium"},
        row.get("import_used_relevance") in {"Strong", "Medium"},
        row.get("evidence_note"),
    ])
    has_c = row.get("reply_status") in {"Replied"} or row.get("lead_status") in {"Ready for Sales", "Sales In Progress"}

    if has_c and has_b:
        return {"lead_grade": "C", "handoff_team": "Export Sales", "reason": "High-intent lead"}
    if has_b:
        return {"lead_grade": "B", "handoff_team": "Customer Service", "reason": "Qualified enhanced lead"}
    if has_base:
        return {"lead_grade": "A", "handoff_team": "None", "reason": "Base lead needs enrichment"}
    return {"lead_grade": "Watch", "handoff_team": "None", "reason": "Insufficient data"}
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
cd apps/api && pytest tests/test_lead_rules.py -v
```

Expected: all tests pass.

### Task 13: Implement Feishu One-Way Sync Mapping

**Files:**
- Create: `apps/api/app/services/feishu_sync.py`
- Create: `apps/api/tests/test_feishu_sync_mapping.py`

- [ ] **Step 1: Write mapping tests**

Write:

```python
from app.services.feishu_sync import map_feishu_record_to_lead

def test_map_feishu_record_to_lead():
    record = {
        "lead_id": "L-001",
        "customer_name": "Moscow Auto",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": "Dealer",
        "lead_grade": "B",
        "lead_status": "Ready for CS",
        "business_activity": "High",
        "scale_signal": "Medium",
        "import_used_relevance": "Strong",
        "evidence_note": "Publishes imported used vehicles.",
        "do_not_contact": "false",
    }
    lead = map_feishu_record_to_lead(record)
    assert lead["external_id"] == "L-001"
    assert lead["customer_name"] == "Moscow Auto"
    assert lead["do_not_contact"] is False
```

- [ ] **Step 2: Implement mapper**

Write:

```python
def _bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}

def map_feishu_record_to_lead(record: dict) -> dict:
    return {
        "external_id": record["lead_id"],
        "customer_name": record["customer_name"],
        "country": record.get("country") or "Russia",
        "city": record.get("city") or None,
        "customer_type": record.get("customer_type") or "Unknown",
        "lead_grade": record.get("lead_grade") or "A",
        "lead_status": record.get("lead_status") or "New",
        "business_activity": record.get("business_activity") or "Unknown",
        "scale_signal": record.get("scale_signal") or "Unknown",
        "import_used_relevance": record.get("import_used_relevance") or "Unknown",
        "evidence_note": record.get("evidence_note") or "",
        "do_not_contact": _bool(record.get("do_not_contact")),
    }
```

- [ ] **Step 3: Run mapping tests**

Run:

```bash
cd apps/api && pytest tests/test_feishu_sync_mapping.py -v
```

Expected: tests pass.

### Task 14: Build CRM Web Views

**Files:**
- Create: `apps/web/src/views/LeadBoard.vue`
- Create: `apps/web/src/views/LeadDetail.vue`
- Create: `apps/web/src/components/AiRecommendationPanel.vue`
- Create: `apps/web/src/components/ComplianceBadge.vue`

- [ ] **Step 1: Implement LeadBoard**

Create a Vue3 view with columns for:

```text
New
Need Enrichment
Need Review
Ready for CS
CS In Progress
Ready for Sales
Sales In Progress
Invalid
Watch
Do Not Contact
```

Each card shows `customer_name`, `lead_grade`, `city`, `source_platform`, `assigned_owner`, and `next_action`.

- [ ] **Step 2: Implement LeadDetail**

Create detail sections:

```text
Customer basics
Source and evidence
Business condition
AI recommendation
Outreach history
Vehicle matching
Compliance and do-not-contact
```

- [ ] **Step 3: Implement AI panel**

The panel must display:

```text
recommended_grade
recommendation_reason
missing_fields
next_action
russian_outreach_draft
risk_note
last_ai_run_at
model_name
evidence_links
```

- [ ] **Step 4: Implement compliance badge**

Display risk levels:

```text
Low: green
Medium: amber
High: red
Forbidden: dark red
```

### Task 15: Build Dashboard Metrics

**Files:**
- Create: `apps/api/app/api/routes/dashboard.py`
- Create: `apps/web/src/views/Dashboard.vue`

- [ ] **Step 1: Define dashboard API metrics**

Route `/dashboard/summary` returns:

```json
{
  "lead_count": 0,
  "grade_counts": {"A": 0, "B": 0, "C": 0, "Invalid": 0, "Watch": 0},
  "channel_counts": [],
  "reply_rate": 0.0,
  "sla_overdue_count": 0,
  "sales_opportunity_count": 0
}
```

- [ ] **Step 2: Build dashboard view**

The dashboard shows four sections:

```text
Channel metrics
Outreach metrics
SLA metrics
Sales opportunity metrics
```

### Task 16: Build Mobile Lead Views

**Files:**
- Create: `apps/mobile/pages/leads/index.vue`
- Create: `apps/mobile/pages/leads/detail.vue`

- [ ] **Step 1: Implement mobile list**

The mobile lead list shows only assigned leads, with filters for:

```text
Ready for CS
CS In Progress
Ready for Sales
Sales In Progress
Overdue
```

- [ ] **Step 2: Implement mobile detail**

Mobile detail shows:

```text
customer_name
lead_grade
primary_contact
next_action
AI recommended message
outreach history
do-not-contact switch
```

### Task 17: Final MVP QA

**Files:**
- Create: `docs/crm/qa-checklist.md`

- [ ] **Step 1: Create QA checklist**

Write:

```markdown
# MVP QA Checklist

## Data Sync

- [ ] Feishu leads sync into PostgreSQL.
- [ ] Duplicates are detected by name + contact.
- [ ] Do Not Contact survives sync.

## Lead Workflow

- [ ] A leads do not auto-handoff.
- [ ] B leads route to customer service.
- [ ] C leads route to export sales.
- [ ] SLA displays correctly: B 48h, C 24h.

## AI

- [ ] AI output stores input, output, model, time, evidence links.
- [ ] AI message drafts do not promise price, logistics, customs, payment, or delivery without approved facts.

## Compliance

- [ ] High-risk channels cannot be selected for automated execution.
- [ ] Do Not Contact leads are excluded from outreach tasks.
- [ ] C-grade quote/contract stage requires compliance review.

## Dashboard

- [ ] Channel metrics load.
- [ ] Reply metrics load.
- [ ] SLA metrics load.
- [ ] Sales opportunity metrics load.
```

- [ ] **Step 2: Run end-to-end acceptance**

Create one A-grade, one B-grade, one C-grade, and one Do-Not-Contact lead. Verify each follows the expected routing and UI behavior in the checklist.

## Execution Handoff

Recommended execution order:

1. Task 0-5: PoC foundation.
2. Task 6-9: PoC execution and retrospective.
3. Task 10-13: Backend and data sync MVP foundation.
4. Task 14-16: Web/mobile CRM views.
5. Task 17: Final MVP QA.

Do not start Task 10 until Task 9 recommends `Continue to MVP`.

