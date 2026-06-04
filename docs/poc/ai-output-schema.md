# PoC AI 输出 JSON Schema

创建日期：2026-05-27  
对应 Story：E2-S1、E2-S2

## 1. 总体原则

AI 输出必须满足：

- 严格 JSON。
- 所有字段名使用英文 snake_case。
- 缺失字段输出 `"Unknown"`、`null` 或空数组 `[]`。
- 不允许编造客户名称、联系方式、意向、价格、物流、清关、付款或交付信息。
- 必须保留来源链接和证据。
- 必须保留审计字段。
- Invalid 和 Watch 不进入触达队列。
- C 级必须标记合规复核。

## 2. 公共枚举

### 2.1 channel_risk_level

```json
["Low", "Medium", "High", "Forbidden"]
```

### 2.2 customer_type

```json
[
  "local_dealer_secondary_dealer",
  "personal_buyer",
  "kol_auto_blogger",
  "unknown",
  "non_target"
]
```

### 2.3 recommended_grade

```json
["A", "B", "C", "Invalid", "Watch"]
```

### 2.4 suggested_handoff_team

```json
["lead_ops", "customer_service", "export_sales", "compliance", "none"]
```

### 2.5 next_action

```json
[
  "enrich_more",
  "handoff_to_customer_service",
  "handoff_to_export_sales",
  "mark_invalid",
  "watch_later",
  "do_not_contact",
  "policy_review_only",
  "manual_small_sample_only"
]
```

## 3. lead_extraction_output

```json
{
  "schema_version": "poc-ai-output-v1",
  "task_type": "lead_extraction",
  "source": {
    "source_url": "https://example.ru/contact",
    "source_platform": "官网",
    "channel_risk_level": "Low",
    "search_keyword": "дилер подержанных автомобилей Москва",
    "collected_at": "2026-05-27T10:00:00+08:00",
    "operator": "AI/Agent 操作负责人"
  },
  "risk_blocked": false,
  "risk_block_reason": null,
  "lead": {
    "customer_name": "Example Auto Moscow",
    "country": "Russia",
    "city": "Moscow",
    "customer_type": "local_dealer_secondary_dealer",
    "business_scope": "Used cars and imported SUVs",
    "sells_used_or_imported_cars": "yes",
    "import_used_relevance": "high",
    "activity_signal": "Website shows updated inventory and contact page",
    "scale_signal": "Multiple vehicle listings shown",
    "contacts": {
      "emails": ["sales@example.ru"],
      "phones": ["+7 999 000 0000"],
      "whatsapp": [],
      "telegram": [],
      "wechat": [],
      "website_forms": ["https://example.ru/contact"]
    },
    "official_website": "https://example.ru",
    "source_evidence": [
      {
        "claim": "dealer_identity",
        "evidence_text": "Used car dealer in Moscow",
        "source_url": "https://example.ru/contact"
      }
    ],
    "missing_fields": ["主营车型", "是否有进口车经验"]
  },
  "recommended_next_action": "send_to_grading",
  "touch_queue_allowed": false,
  "audit": {
    "model": "Unknown",
    "prompt_version": "lead-extraction-v1",
    "input_saved": true,
    "output_saved": true,
    "executed_at": "2026-05-27T10:05:00+08:00"
  }
}
```

### 3.1 字段要求

| 字段 | 必填 | 规则 |
|---|---:|---|
| source.source_url | 是 | 必须来自人工提供输入 |
| source.channel_risk_level | 是 | Low/Medium/High/Forbidden |
| risk_blocked | 是 | High/Forbidden 必须为 true |
| lead.customer_name | 是 | 不确定输出 Unknown |
| lead.country | 是 | 第一阶段通常为 Russia，不确定输出 Unknown |
| lead.city | 是 | 不确定输出 Unknown |
| lead.customer_type | 是 | 使用枚举 |
| lead.contacts | 是 | 缺失联系方式输出空数组 |
| lead.activity_signal | 是 | 无证据输出 Unknown |
| lead.scale_signal | 是 | 无证据输出 Unknown |
| lead.import_used_relevance | 是 | high/medium/low/unknown |
| lead.source_evidence | 是 | 至少 1 条；无证据时线索应进入 Invalid 或 Watch |
| audit | 是 | 必须保留模型、prompt 版本、执行时间 |

## 4. lead_grading_output

```json
{
  "schema_version": "poc-ai-output-v1",
  "task_type": "lead_grading",
  "lead_id": "LEAD-0001",
  "recommended_grade": "B",
  "recommended_reason": "客户有公开官网、联系方式和二手车库存信号，适合客服人工触达。",
  "reason_codes": ["has_public_contact", "used_car_signal", "dealer_identity"],
  "evidence_refs": [
    {
      "claim": "used_car_signal",
      "evidence_text": "автомобили с пробегом",
      "source_url": "https://example.ru"
    }
  ],
  "missing_fields": ["是否有进口车经验", "主营车型明细"],
  "next_action": "handoff_to_customer_service",
  "suggested_handoff_team": "customer_service",
  "touch_queue_allowed": true,
  "touch_channel_limit": "manual_only_low_medium_risk",
  "compliance_review_required": false,
  "human_review_required": true,
  "risk_flags": [],
  "audit": {
    "model": "Unknown",
    "prompt_version": "lead-grading-v1",
    "input_saved": true,
    "output_saved": true,
    "executed_at": "2026-05-27T10:10:00+08:00"
  }
}
```

### 4.1 等级与动作约束

| 推荐等级 | touch_queue_allowed | next_action | suggested_handoff_team | compliance_review_required |
|---|---|---|---|---|
| A | false | enrich_more | lead_ops | false |
| B | true | handoff_to_customer_service | customer_service | false |
| C | true | handoff_to_export_sales | export_sales | true |
| Invalid | false | mark_invalid | none | false |
| Watch | false | watch_later | lead_ops | false |

### 4.2 强制阻断规则

以下情况 `touch_queue_allowed` 必须为 false：

- recommended_grade 为 Invalid。
- recommended_grade 为 Watch。
- do_not_contact 为 true。
- channel_risk_level 为 High。
- channel_risk_level 为 Forbidden。
- 来源链接缺失。
- 来源证据缺失。
- 联系方式疑似由 AI 推测而非来源文本提供。

### 4.3 C 级合规复核规则

当 `recommended_grade = "C"`：

- `compliance_review_required` 必须为 true。
- `risk_flags` 必须包含 `"c_grade_requires_compliance_review"`。
- `recommended_reason` 必须说明进入 C 级的证据。
- 不得输出可报价、可签约或可成交结论。

## 5. 审计保存要求

每次 AI 执行必须保存：

- 输入文本。
- 来源链接。
- 渠道风险等级。
- Prompt 文件版本。
- 模型名称。
- 输出 JSON。
- 执行时间。
- 操作人。
- 是否被阻断。

## 6. 人工复核字段建议

飞书或后续 PostgreSQL 建议保留：

```json
{
  "human_review": {
    "review_status": "pending",
    "reviewer": "Unknown",
    "reviewed_at": null,
    "original_ai_grade": "B",
    "final_grade": null,
    "override_reason": null
  }
}
```

## 7. E2-S1 / E2-S2 验收清单

- [x] AI 输出包含客户名称、国家、城市、客户类型、联系方式、活跃度、规模信号、进口/二手相关性、来源证据。
- [x] AI 输出包含推荐等级、推荐原因、缺失信息、下一步动作、建议交付团队。
- [x] 缺失字段要求输出 Unknown、null 或空数组。
- [x] 明确不允许编造。
- [x] Invalid 和 Watch 不进入触达队列。
- [x] C 级必须标记合规复核。
- [x] AI 输入、输出、模型、时间和来源链接必须审计保存。

