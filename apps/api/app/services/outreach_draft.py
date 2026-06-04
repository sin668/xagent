from datetime import datetime
from uuid import UUID


BLOCKED_RISK_LEVELS = {"High", "Forbidden"}
FORBIDDEN_COMMITMENTS = (
    "финальную цену",
    "быструю доставку",
    "таможенное оформление",
    "безопасную оплату",
    "final price",
    "customs clearance",
    "payment safety",
    "delivery time",
    "最终价格",
    "物流时效",
    "清关",
    "付款安全",
    "交付周期",
)


class OutreachDraftService:
    def get_existing_draft(
        self,
        *,
        customer_id: UUID,
        risk_level: str = "Low",
        do_not_contact: bool = False,
        rag_context: dict | None = None,
    ) -> dict:
        draft = {
            "draft_id": "draft-ru-b-001",
            "customer_id": customer_id,
            "customer_name": "AutoCity Moscow",
            "template_id": "TMP-RU-B-001",
            "template_status": "可外发",
            "version": "v1",
            "generated_at": "2026-05-28T12:00:00Z",
            "subject": "Поставка подержанных автомобилей из Китая",
            "body": (
                "Здравствуйте! Мы изучаем возможности сотрудничества с автодилерами по поставкам автомобилей "
                "с пробегом, почти новых и складских автомобилей. Если вам интересно, пожалуйста, сообщите, "
                "какие модели и форматы сотрудничества для вас актуальны."
            ),
            "refusal_path": (
                "Если вам не интересно получать такие сообщения, пожалуйста, сообщите нам, "
                "и мы больше не будем вас беспокоить."
            ),
            "risk_tips": ["仅人工发送", "不得承诺最终价格、物流时效、清关结果、付款安全或交付周期"],
            "audit": {
                "model": "Unknown",
                "prompt_version": "outreach-template-v1",
                "input_saved": True,
                "output_saved": True,
                "rag_context": rag_context
                or {
                    "context_status": "empty_context",
                    "knowledge_item_refs": [],
                    "context_text": "",
                },
            },
        }
        return self.build_view_model(draft=draft, risk_level=risk_level, do_not_contact=do_not_contact)

    def build_view_model(self, *, draft: dict, risk_level: str, do_not_contact: bool) -> dict:
        block_reasons = []
        if do_not_contact:
            block_reasons.append("客户已标记勿扰")
        if risk_level in BLOCKED_RISK_LEVELS:
            block_reasons.append("渠道风险不允许触达动作")

        compliance_checks = [
            {
                "key": "no_forbidden_commitments",
                "label": "未承诺价格/物流/清关/付款/交付周期",
                "passed": not self.has_forbidden_commitments(draft),
            },
            {"key": "has_refusal_path", "label": "包含拒绝联系路径", "passed": bool(draft["refusal_path"])},
            {"key": "channel_allowed", "label": "渠道风险允许人工触达", "passed": risk_level not in BLOCKED_RISK_LEVELS},
            {"key": "customer_not_dnc", "label": "客户未标记勿扰", "passed": not do_not_contact},
            {
                "key": "audit_saved",
                "label": "AI 输入输出审计已保存",
                "passed": bool(draft["audit"]["input_saved"] and draft["audit"]["output_saved"]),
            },
            {"key": "template_approved", "label": "模板状态可外发", "passed": draft["template_status"] == "可外发"},
        ]
        can_generate_draft = not block_reasons
        can_record_sent = can_generate_draft and all(check["passed"] for check in compliance_checks)

        return {
            **draft,
            "compliance_checks": compliance_checks,
            "block_reasons": block_reasons,
            "can_generate_draft": can_generate_draft,
            "can_record_sent": can_record_sent,
            "manual_only": True,
            "auto_send_enabled": False,
        }

    def record_manual_send(
        self,
        *,
        customer_id: UUID,
        human_confirmed: bool,
        sender: str,
        channel: str,
        risk_level: str = "Low",
        do_not_contact: bool = False,
    ) -> dict:
        draft = self.get_existing_draft(customer_id=customer_id, risk_level=risk_level, do_not_contact=do_not_contact)
        if not human_confirmed or not draft["can_record_sent"]:
            raise ValueError("Manual confirmation and passing compliance checks are required before recording sent outreach.")

        return {
            "customer_id": customer_id,
            "draft_id": draft["draft_id"],
            "template_id": draft["template_id"],
            "status": "sent_manual",
            "sender": sender,
            "channel": channel,
            "sent_at": datetime.utcnow().isoformat(),
            "auto_send": False,
        }

    @staticmethod
    def has_forbidden_commitments(draft: dict) -> bool:
        text = f"{draft.get('subject', '')}\n{draft.get('body', '')}\n{draft.get('refusal_path', '')}".lower()
        return any(pattern.lower() in text for pattern in FORBIDDEN_COMMITMENTS)
