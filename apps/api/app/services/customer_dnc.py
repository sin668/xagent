from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, OutreachRecord
from app.models.enums import ContactMethodType, CustomerGrade, CustomerStatus, OutreachStatus
from app.services.audit_events import Phase3AuditEventService
from app.services.compliance_guards import Phase3ComplianceGuardService
from app.services.permissions import Phase3Action, Phase3PermissionService


class CustomerDncService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_customer(self, customer_id: UUID) -> Customer:
        customer = self.session.scalar(select(Customer).where(Customer.id == customer_id))
        if customer is None:
            raise ValueError(f"客户不存在: {customer_id}")
        return customer

    def mark_do_not_contact(self, *, customer_id: UUID, marked_by: str, reason: str) -> Customer:
        if not reason.strip():
            raise ValueError("标记勿扰需要记录原因。")
        customer = self.get_customer(customer_id)
        customer.do_not_contact = True
        customer.do_not_contact_reason = reason
        customer.do_not_contact_marked_by = marked_by
        customer.do_not_contact_marked_at = datetime.utcnow()
        customer.status = CustomerStatus.DO_NOT_CONTACT
        Phase3AuditEventService.record_event(
            self.session,
            event_name="customer_do_not_contact_marked",
            actor=marked_by,
            entity_type="customer",
            entity_id=customer.id,
            reason=reason,
            evidence={
                "status": CustomerStatus.DO_NOT_CONTACT.value,
                "customer_name": customer.name,
                "marked_by": marked_by,
            },
            occurred_at=customer.do_not_contact_marked_at,
        )
        return customer

    def unmark_do_not_contact(self, *, customer_id: UUID, unmarked_by: str, reason: str, actor_role: str = "operations") -> Customer:
        if not reason.strip():
            raise ValueError("取消勿扰需要记录原因。")
        Phase3PermissionService.ensure_allowed(Phase3Action.CANCEL_DO_NOT_CONTACT, actor_role=actor_role)
        customer = self.get_customer(customer_id)
        customer.do_not_contact = False
        customer.do_not_contact_reason = f"取消勿扰：{reason}"
        customer.do_not_contact_marked_by = unmarked_by
        customer.do_not_contact_marked_at = datetime.utcnow()
        if customer.status == CustomerStatus.DO_NOT_CONTACT:
            customer.status = CustomerStatus.PENDING_REVIEW
        return customer

    def list_outreach_candidates(self) -> list[Customer]:
        return list(
            self.session.scalars(
                select(Customer)
                .where(
                    Customer.do_not_contact.is_(False),
                    Customer.grade.in_([CustomerGrade.B, CustomerGrade.C]),
                    Customer.status.in_(
                        [
                            CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
                            CustomerStatus.READY_FOR_SALES,
                            CustomerStatus.CUSTOMER_SERVICE_FOLLOWING,
                            CustomerStatus.SALES_FOLLOWING,
                        ]
                    ),
                )
                .order_by(Customer.updated_at.desc(), Customer.name)
            ).all()
        )

    def list_ai_script_candidates(self) -> list[Customer]:
        return self.list_outreach_candidates()

    def list_customers(self, *, limit: int = 100) -> list[Customer]:
        return list(
            self.session.scalars(
                select(Customer)
                .order_by(Customer.updated_at.desc(), Customer.created_at.desc(), Customer.name.asc())
                .limit(limit)
            ).all()
        )

    def record_outreach_result(
        self,
        *,
        customer_id: UUID,
        channel: str,
        status: str,
        sent_by: str | None = None,
        owner: str | None = None,
        response_summary: str | None = None,
        next_action: str | None = None,
        do_not_contact_reason: str | None = None,
        external_id: str | None = None,
        manual_confirmed: bool = False,
        script_version: str | None = None,
    ) -> OutreachRecord:
        customer = self.get_customer(customer_id)
        Phase3ComplianceGuardService.ensure_customer_can_receive_outreach(
            customer,
            session=self.session,
            actor=sent_by or owner,
            action="outreach_record_create",
        )
        outreach_status = OutreachStatus(status)
        Phase3ComplianceGuardService.ensure_outreach_is_not_automatic(
            outreach_status,
            manual_confirmed=manual_confirmed,
            session=self.session,
            actor=sent_by or owner,
            target_ref=f"customer:{customer.id}",
        )
        outreach = OutreachRecord(
            external_id=external_id,
            customer_id=customer.id,
            channel=ContactMethodType(channel),
            status=outreach_status,
            sent_by=sent_by,
            owner=owner,
            script_version=script_version,
            response_summary=response_summary,
            next_action=next_action,
            triggers_do_not_contact=False,
            do_not_contact_reason=do_not_contact_reason,
        )
        if outreach.status == OutreachStatus.REJECTED or next_action == "标记勿扰":
            reason = do_not_contact_reason or response_summary or "客户拒绝继续联系"
            outreach.triggers_do_not_contact = True
            outreach.do_not_contact_reason = reason
            customer.do_not_contact = True
            customer.do_not_contact_reason = reason
            customer.do_not_contact_marked_by = sent_by
            customer.do_not_contact_marked_at = datetime.utcnow()
            customer.status = CustomerStatus.DO_NOT_CONTACT
        self.session.add(outreach)
        return outreach

    def list_outreach_records(self, customer_id: UUID) -> list[OutreachRecord]:
        self.get_customer(customer_id)
        return list(
            self.session.scalars(
                select(OutreachRecord)
                .where(OutreachRecord.customer_id == customer_id)
                .order_by(OutreachRecord.created_at.asc(), OutreachRecord.id.asc())
            ).all()
        )
