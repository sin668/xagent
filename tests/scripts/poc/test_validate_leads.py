import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.poc.validate_leads import (
    REQUIRED_FIELDS,
    VALID_GRADES,
    analyze_leads,
    normalize_contact_key,
    source_domain,
)


class ValidateLeadsTest(unittest.TestCase):
    def test_source_domain_normalizes_urls(self):
        self.assertEqual(source_domain("https://www.example.ru/contact?utm=1"), "example.ru")
        self.assertEqual(source_domain("http://dealer.example.ru/path"), "dealer.example.ru")
        self.assertEqual(source_domain(""), "")

    def test_normalize_contact_key_prefers_email_then_phone_then_other_contacts(self):
        self.assertEqual(
            normalize_contact_key({"邮箱": " Sales@Example.RU ", "电话": "+7 999 123"}),
            "email:sales@example.ru",
        )
        self.assertEqual(normalize_contact_key({"邮箱": "", "电话": "+7 (999) 123-45-67"}), "phone:79991234567")
        self.assertEqual(normalize_contact_key({"Telegram": " @Dealer_Name "}), "telegram:@dealer_name")
        self.assertEqual(normalize_contact_key({}), "")

    def test_analyze_leads_validates_required_fields_url_grade_and_do_not_contact_reason(self):
        rows = [
        {
            "线索ID": "LEAD-0001",
            "客户名称": "",
            "国家": "Russia",
            "城市/地区": "Moscow",
            "客户类型": "当地车商/二级经销商",
            "线索等级": "Hot",
            "线索状态": "待复核",
            "邮箱": "sales@example.ru",
            "电话": "",
            "WhatsApp": "",
            "Telegram": "",
            "官网": "https://example.ru",
            "来源链接": "not-a-url",
            "来源证据备注": "",
            "是否勿扰": "是",
            "勿扰原因": "",
            "AI 推荐等级": "B",
            "人工复核结果": "未复核",
        }
        ]

        report = analyze_leads(rows)

        self.assertEqual(report["summary"]["total_rows"], 1)
        self.assertEqual(report["summary"]["error_count"], 4)
        messages = [issue["message"] for issue in report["issues"]]
        self.assertIn("必填字段缺失：客户名称", messages)
        self.assertIn("必填字段缺失：来源证据备注", messages)
        self.assertIn("来源链接不是有效 URL", messages)
        self.assertIn("线索等级不合法：Hot", messages)
        self.assertEqual(report["summary"]["warning_count"], 1)
        self.assertEqual(report["warnings"][0]["message"], "已标记勿扰但缺少勿扰原因")


    def test_analyze_leads_detects_strong_and_suspected_duplicates_without_deleting_rows(self):
        rows = [
        {
            "线索ID": "LEAD-0001",
            "客户名称": "Avto Premium",
            "国家": "Russia",
            "城市/地区": "Moscow",
            "客户类型": "当地车商/二级经销商",
            "线索等级": "B",
            "线索状态": "待复核",
            "邮箱": "sales@avto.example.ru",
            "电话": "",
            "WhatsApp": "",
            "Telegram": "",
            "官网": "https://avto.example.ru",
            "来源链接": "https://avto.example.ru/contact",
            "来源证据备注": "公开页面展示二手车库存",
            "是否勿扰": "否",
            "勿扰原因": "",
            "AI 推荐等级": "B",
            "人工复核结果": "通过",
        },
        {
            "线索ID": "LEAD-0002",
            "客户名称": " avto premium ",
            "国家": "Russia",
            "城市/地区": "Moscow",
            "客户类型": "当地车商/二级经销商",
            "线索等级": "A",
            "线索状态": "待补全",
            "邮箱": "SALES@AVTO.EXAMPLE.RU",
            "电话": "",
            "WhatsApp": "",
            "Telegram": "",
            "官网": "https://avto.example.ru",
            "来源链接": "https://avto.example.ru/about",
            "来源证据备注": "公开页面展示联系方式",
            "是否勿扰": "否",
            "勿扰原因": "",
            "AI 推荐等级": "A",
            "人工复核结果": "未复核",
        },
        {
            "线索ID": "LEAD-0003",
            "客户名称": "Avto Premium",
            "国家": "Russia",
            "城市/地区": "Moscow",
            "客户类型": "当地车商/二级经销商",
            "线索等级": "Watch",
            "线索状态": "沉淀观察",
            "邮箱": "",
            "电话": "+7 999 000 0000",
            "WhatsApp": "",
            "Telegram": "",
            "官网": "https://avto.example.ru",
            "来源链接": "https://avto.example.ru/inventory",
            "来源证据备注": "公开页面展示库存",
            "是否勿扰": "否",
            "勿扰原因": "",
            "AI 推荐等级": "Watch",
            "人工复核结果": "退回补全",
        },
        ]

        report = analyze_leads(rows)

        self.assertEqual(report["summary"]["total_rows"], 3)
        self.assertEqual(report["summary"]["rows_retained"], 3)
        self.assertEqual(report["summary"]["strong_duplicate_group_count"], 1)
        self.assertEqual(report["summary"]["suspected_duplicate_group_count"], 1)
        self.assertEqual(report["strong_duplicates"][0]["lead_ids"], ["LEAD-0001", "LEAD-0002"])
        self.assertEqual(report["suspected_duplicates"][0]["lead_ids"], ["LEAD-0001", "LEAD-0002", "LEAD-0003"])


    def test_analyze_leads_summarizes_failed_cases(self):
        rows = [
        {
            "线索ID": "LEAD-0001",
            "客户名称": "Repair Shop",
            "国家": "Russia",
            "城市/地区": "Kazan",
            "客户类型": "非目标",
            "线索等级": "Invalid",
            "线索状态": "无效/暂不匹配",
            "邮箱": "",
            "电话": "",
            "WhatsApp": "",
            "Telegram": "",
            "官网": "https://repair.example.ru",
            "来源链接": "https://repair.example.ru",
            "来源证据备注": "维修服务，不销售车辆",
            "是否勿扰": "否",
            "勿扰原因": "",
            "AI 推荐等级": "B",
            "人工复核结果": "无效",
            "人工复核备注": "维修",
        },
        {
            "线索ID": "LEAD-0002",
            "客户名称": "Parts Shop",
            "国家": "Russia",
            "城市/地区": "Kazan",
            "客户类型": "非目标",
            "线索等级": "Invalid",
            "线索状态": "无效/暂不匹配",
            "邮箱": "",
            "电话": "",
            "WhatsApp": "",
            "Telegram": "",
            "官网": "https://parts.example.ru",
            "来源链接": "https://parts.example.ru",
            "来源证据备注": "配件销售",
            "是否勿扰": "否",
            "勿扰原因": "",
            "AI 推荐等级": "C",
            "人工复核结果": "无效",
            "人工复核备注": "配件",
        },
        ]

        report = analyze_leads(rows)

        self.assertEqual(report["summary"]["failed_case_count"], 2)
        self.assertEqual(report["failed_case_summary"]["维修"], 1)
        self.assertEqual(report["failed_case_summary"]["配件"], 1)
        self.assertEqual(report["ai_misclassification_count"], 2)
        self.assertEqual(report["ai_misclassifications"][0]["ai_grade"], "B")


    def test_cli_outputs_json_report(self):
        import tempfile

        tmp_path = Path(tempfile.mkdtemp())
        csv_path = tmp_path / "leads.csv"
        report_path = tmp_path / "report.json"
        fieldnames = [
        "线索ID",
        *REQUIRED_FIELDS,
        "线索等级",
        "线索状态",
        "邮箱",
        "电话",
        "WhatsApp",
        "Telegram",
        "官网",
        "是否勿扰",
        "勿扰原因",
        "AI 推荐等级",
        "人工复核结果",
        "人工复核备注",
        ]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(
                {
                    "线索ID": "LEAD-0001",
                    "客户名称": "Example Dealer",
                    "国家": "Russia",
                    "城市/地区": "Moscow",
                    "客户类型": "当地车商/二级经销商",
                    "线索等级": "B",
                    "线索状态": "待复核",
                    "邮箱": "sales@example.ru",
                    "电话": "",
                    "WhatsApp": "",
                    "Telegram": "",
                    "官网": "https://example.ru",
                    "来源链接": "https://example.ru/contact",
                    "来源证据备注": "公开库存页面",
                    "是否勿扰": "否",
                    "勿扰原因": "",
                    "AI 推荐等级": "B",
                    "人工复核结果": "通过",
                    "人工复核备注": "",
                }
            )

        result = subprocess.run(
            [sys.executable, "scripts/poc/validate_leads.py", str(csv_path), "--output", str(report_path)],
            cwd=Path(__file__).resolve().parents[3],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("total_rows=1", result.stdout)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["total_rows"], 1)
        self.assertEqual(report["summary"]["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
