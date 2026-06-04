#!/usr/bin/env python3
"""Validate PoC lead CSV files and report duplicate/failed-case signals.

The script is intentionally non-destructive: it reads a CSV and writes a JSON
report, but never modifies or deletes lead rows.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REQUIRED_FIELDS = [
    "客户名称",
    "国家",
    "城市/地区",
    "客户类型",
    "来源链接",
    "来源证据备注",
]

VALID_GRADES = {"A", "B", "C", "Invalid", "Watch"}

FAILED_CASE_REASONS = [
    "维修",
    "配件",
    "保险",
    "招聘",
    "媒体",
    "重复",
    "无联系方式",
    "租车",
    "驾校",
    "洗车",
    "非车辆销售",
    "无效",
]


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", " ", normalize_text(value).casefold())


def normalize_phone(value: Any) -> str:
    return re.sub(r"\D+", "", normalize_text(value))


def normalize_contact_key(row: dict[str, Any]) -> str:
    email = normalize_text(row.get("邮箱")).casefold()
    if email:
        return f"email:{email}"

    phone = normalize_phone(row.get("电话"))
    if phone:
        return f"phone:{phone}"

    whatsapp = normalize_phone(row.get("WhatsApp"))
    if whatsapp:
        return f"whatsapp:{whatsapp}"

    telegram = normalize_text(row.get("Telegram")).casefold()
    if telegram:
        return f"telegram:{telegram}"

    website = normalize_text(row.get("官网")).lower()
    if website:
        return f"website:{source_domain(website)}"

    return ""


def source_domain(url: Any) -> str:
    value = normalize_text(url)
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_valid_url(url: Any) -> bool:
    value = normalize_text(url)
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def truthy(value: Any) -> bool:
    return normalize_text(value).casefold() in {"是", "yes", "true", "1", "y"}


def lead_id(row: dict[str, Any], index: int) -> str:
    return normalize_text(row.get("线索ID")) or f"ROW-{index + 1}"


def infer_failed_reason(row: dict[str, Any]) -> str:
    text = " ".join(
        normalize_text(row.get(field))
        for field in ["人工复核备注", "来源证据备注", "客户类型", "线索状态", "备注"]
    )
    for reason in FAILED_CASE_REASONS:
        if reason in text:
            return reason
    if normalize_text(row.get("线索等级")) == "Invalid":
        return "无效"
    return "未分类"


def add_issue(
    bucket: list[dict[str, Any]],
    *,
    row_number: int,
    lead_id_value: str,
    field: str,
    message: str,
    severity: str,
) -> None:
    bucket.append(
        {
            "row_number": row_number,
            "lead_id": lead_id_value,
            "field": field,
            "message": message,
            "severity": severity,
        }
    )


def duplicate_groups(groups: dict[tuple[str, ...], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    result = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        result.append(
            {
                "key": " | ".join(key),
                "lead_ids": [m["lead_id"] for m in members],
                "row_numbers": [m["row_number"] for m in members],
                "review_action": "人工复核：合并、忽略或保留观察；不得自动删除。",
            }
        )
    return result


def analyze_leads(rows: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    strong_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    suspected_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    failed_case_summary: Counter[str] = Counter()
    failed_cases: list[dict[str, Any]] = []
    ai_misclassifications: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        row_number = index + 2
        current_id = lead_id(row, index)

        for field in REQUIRED_FIELDS:
            if not normalize_text(row.get(field)):
                add_issue(
                    issues,
                    row_number=row_number,
                    lead_id_value=current_id,
                    field=field,
                    message=f"必填字段缺失：{field}",
                    severity="error",
                )

        source_url = row.get("来源链接")
        if source_url and not is_valid_url(source_url):
            add_issue(
                issues,
                row_number=row_number,
                lead_id_value=current_id,
                field="来源链接",
                message="来源链接不是有效 URL",
                severity="error",
            )

        grade = normalize_text(row.get("线索等级"))
        if grade and grade not in VALID_GRADES:
            add_issue(
                issues,
                row_number=row_number,
                lead_id_value=current_id,
                field="线索等级",
                message=f"线索等级不合法：{grade}",
                severity="error",
            )

        if truthy(row.get("是否勿扰")) and not normalize_text(row.get("勿扰原因")):
            add_issue(
                warnings,
                row_number=row_number,
                lead_id_value=current_id,
                field="勿扰原因",
                message="已标记勿扰但缺少勿扰原因",
                severity="warning",
            )

        contact_key = normalize_contact_key(row)
        name_key = normalize_name(row.get("客户名称"))
        if name_key and contact_key:
            strong_groups[(name_key, contact_key)].append({"lead_id": current_id, "row_number": row_number})

        city_key = normalize_text(row.get("城市/地区")).casefold()
        domain_key = source_domain(row.get("来源链接"))
        if name_key and city_key and domain_key:
            suspected_groups[(name_key, city_key, domain_key)].append(
                {"lead_id": current_id, "row_number": row_number}
            )

        if grade == "Invalid" or "无效" in normalize_text(row.get("线索状态")):
            reason = infer_failed_reason(row)
            failed_case_summary[reason] += 1
            failed_cases.append(
                {
                    "lead_id": current_id,
                    "row_number": row_number,
                    "customer_name": normalize_text(row.get("客户名称")),
                    "source_url": normalize_text(row.get("来源链接")),
                    "invalid_reason": reason,
                    "ai_grade": normalize_text(row.get("AI 推荐等级")) or "Unknown",
                    "human_review": normalize_text(row.get("人工复核结果")) or "Unknown",
                    "suggested_rule_update": "同步到排除关键词或审核规则复盘。",
                }
            )

            ai_grade = normalize_text(row.get("AI 推荐等级"))
            if ai_grade and ai_grade != "Invalid":
                ai_misclassifications.append(
                    {
                        "lead_id": current_id,
                        "row_number": row_number,
                        "customer_name": normalize_text(row.get("客户名称")),
                        "ai_grade": ai_grade,
                        "human_grade": "Invalid",
                        "reason": reason,
                    }
                )

    strong_duplicates = duplicate_groups(strong_groups)
    suspected_duplicates = duplicate_groups(suspected_groups)

    return {
        "summary": {
            "total_rows": len(rows),
            "rows_retained": len(rows),
            "error_count": len(issues),
            "warning_count": len(warnings),
            "strong_duplicate_group_count": len(strong_duplicates),
            "suspected_duplicate_group_count": len(suspected_duplicates),
            "failed_case_count": len(failed_cases),
        },
        "valid_grade_values": sorted(VALID_GRADES),
        "required_fields": REQUIRED_FIELDS,
        "issues": issues,
        "warnings": warnings,
        "strong_duplicates": strong_duplicates,
        "suspected_duplicates": suspected_duplicates,
        "failed_case_summary": dict(failed_case_summary),
        "failed_cases": failed_cases,
        "ai_misclassification_count": len(ai_misclassifications),
        "ai_misclassifications": ai_misclassifications,
        "notes": [
            "本报告只提示重复和失败案例，不会删除或修改原始 CSV。",
            "强重复规则：客户名称 + 联系方式。",
            "疑似重复规则：客户名称 + 城市 + 来源域名。",
        ],
    }


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PoC lead CSV and output a JSON report.")
    parser.add_argument("csv_path", type=Path, help="Path to the lead CSV file.")
    parser.add_argument("--output", type=Path, help="Path to write JSON report. Defaults to stdout only.")
    args = parser.parse_args()

    rows = read_csv(args.csv_path)
    report = analyze_leads(rows)
    payload = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(
        "validation complete: "
        f"total_rows={report['summary']['total_rows']} "
        f"errors={report['summary']['error_count']} "
        f"warnings={report['summary']['warning_count']} "
        f"strong_duplicates={report['summary']['strong_duplicate_group_count']} "
        f"suspected_duplicates={report['summary']['suspected_duplicate_group_count']} "
        f"failed_cases={report['summary']['failed_case_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
