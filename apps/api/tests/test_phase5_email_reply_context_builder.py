from datetime import UTC, datetime, timedelta

from app.models.customer import Customer
from app.models.customer_vehicle_intent import CustomerVehicleIntent
from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.models.enums import (
    ChannelRiskLevel,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    CustomerVehicleIntentSourceType,
    CustomerVehicleIntentStatus,
    EmailMessageDirection,
    EmailMessageSourceType,
    EmailMessageStatus,
    EmailThreadStatus,
    OutreachStatus,
    SourcePlatform,
)
from app.models.lead_source import LeadSource
from app.models.outreach_record import OutreachRecord
from app.services.email_reply_context import EmailReplyContextBuilder


def _customer() -> Customer:
    customer = Customer(
        name="Moscow Auto Dealer",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        grade=CustomerGrade.B,
        status=CustomerStatus.READY_FOR_SALES,
        do_not_contact=False,
        owner="销售A",
        owner_team="sales",
    )
    customer.sources = [
        LeadSource(
            platform=SourcePlatform.OFFICIAL_WEBSITE,
            source_url="https://dealer.example.ru",
            source_title="Dealer official site",
            evidence_note="官网公开邮箱和库存信息。",
            channel_risk_level=ChannelRiskLevel.LOW,
            collected_by="agent",
        ),
        LeadSource(
            platform=SourcePlatform.YOUTUBE,
            source_url="https://youtube.example/channel",
            source_title=None,
            evidence_note="公开视频描述含联系方式。",
            channel_risk_level=ChannelRiskLevel.MEDIUM,
            collected_by="agent",
        ),
    ]
    now = datetime(2026, 6, 5, 8, 0, tzinfo=UTC)
    customer.outreach_records = [
        OutreachRecord(
            channel=ContactMethodType.EMAIL,
            status=OutreachStatus.SENT,
            sent_by="销售A",
            sent_at=now - timedelta(days=index),
            response_summary=f"触达记录 {index}",
            next_action="等待回复",
        )
        for index in range(7)
    ]
    customer.vehicle_intents = [
        CustomerVehicleIntent(
            brand="Toyota",
            model="Land Cruiser",
            quantity=2,
            delivery_country="Russia",
            delivery_city="Moscow",
            concerns=["交付周期", "车况"],
            source_type=CustomerVehicleIntentSourceType.MANUAL_CUSTOMER_REPLY,
            source_note="客户邮件提到采购需求",
            status=CustomerVehicleIntentStatus.ACTIVE,
            created_by="运营A",
        )
    ]
    return customer


def _message(customer: Customer) -> EmailMessage:
    thread = EmailThread(
        customer=customer,
        subject="Looking for Toyota SUVs",
        status=EmailThreadStatus.OPEN,
        channel_account="sales@example.com",
        last_message_at=datetime(2026, 6, 5, 8, 30, tzinfo=UTC),
    )
    return EmailMessage(
        thread=thread,
        customer=customer,
        direction=EmailMessageDirection.INBOUND,
        from_email="dealer@example.ru",
        to_emails=["sales@example.com"],
        subject="Looking for Toyota SUVs",
        body_text="Hello, do you have Toyota Land Cruiser options?",
        language="en",
        status=EmailMessageStatus.PENDING_REPLY,
        source_type=EmailMessageSourceType.MAILBOX_SYNC,
    )


def test_email_reply_context_builder_includes_customer_message_sources_intents_and_default_five_outreach_records() -> None:
    customer = _customer()
    message = _message(customer)
    knowledge_hits = [{"title": "FAQ shipping", "version": "v2", "similarity_score": 0.88}]

    context = EmailReplyContextBuilder.build(
        customer=customer,
        message=message,
        knowledge_hits=knowledge_hits,
        risk_decision={"route": "hold_for_manual_review", "block_reasons": []},
    )

    assert context["customer"]["name"] == "Moscow Auto Dealer"
    assert context["customer"]["grade"] == "B"
    assert context["customer"]["do_not_contact"]["enabled"] is False
    assert context["inbound_message"]["subject"] == "Looking for Toyota SUVs"
    assert context["inbound_message"]["body_text"] == "Hello, do you have Toyota Land Cruiser options?"
    assert len(context["recent_outreach_history"]) == 5
    assert context["recent_outreach_history"][0]["response_summary"] == "触达记录 0"
    assert context["vehicle_intents"][0]["brand"] == "Toyota"
    assert context["source_risk"]["highest_risk_level"] == "Medium"
    assert context["knowledge_hits"] == knowledge_hits
    assert context["audit_summary"]["recent_outreach_count"] == 5
    assert context["audit_summary"]["included_sections"] == [
        "customer",
        "inbound_message",
        "recent_outreach_history",
        "vehicle_intents",
        "source_risk",
        "knowledge_hits",
        "risk_decision",
    ]


def test_email_reply_context_builder_normalizes_missing_fields_to_unknown_null_and_empty_arrays() -> None:
    customer = Customer(
        name="Unknown Dealer",
        country="Russia",
        city=None,
        customer_type=CustomerType.UNKNOWN,
        grade=CustomerGrade.WATCH,
        status=CustomerStatus.WATCH,
        do_not_contact=True,
        do_not_contact_reason=None,
    )
    message = EmailMessage(
        thread=EmailThread(subject="Unknown", status=EmailThreadStatus.OPEN),
        customer=customer,
        direction=EmailMessageDirection.INBOUND,
        from_email="unknown@example.ru",
        to_emails=[],
        subject="Unknown",
        body_text="",
        language=None,
        status=EmailMessageStatus.RECEIVED,
        source_type=EmailMessageSourceType.MANUAL,
    )

    context = EmailReplyContextBuilder.build(customer=customer, message=message, knowledge_hits=[], risk_decision=None)

    assert context["customer"]["city"] == "Unknown"
    assert context["customer"]["owner"] == "Unknown"
    assert context["customer"]["do_not_contact"]["reason"] is None
    assert context["inbound_message"]["language"] == "Unknown"
    assert context["recent_outreach_history"] == []
    assert context["vehicle_intents"] == []
    assert context["source_risk"]["sources"] == []
    assert context["source_risk"]["highest_risk_level"] == "Unknown"
    assert context["knowledge_hits"] == []
    assert context["risk_decision"] == {}
    assert context["audit_summary"]["sensitive_data_policy"] == "只包含邮件回复所需客户、来信、触达、意向、来源风险和知识命中摘要。"
