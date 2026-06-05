from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeItem
from app.models.enums import KnowledgeItemStatus, KnowledgeReviewStatus
from app.services.knowledge import KnowledgeService


@dataclass(frozen=True)
class KnowledgeImportSpec:
    collection_name: str
    title: str
    body: str
    language: str
    country: str
    applicable_channels: list[str]
    source_ref: str
    status: KnowledgeItemStatus = KnowledgeItemStatus.DRAFT
    review_status: KnowledgeReviewStatus = KnowledgeReviewStatus.PENDING
    version: str = "phase-1-v1"

    @property
    def rag_eligible(self) -> bool:
        return KnowledgeService.is_rag_eligible(status=self.status, review_status=self.review_status)


@dataclass(frozen=True)
class KnowledgeImportResult:
    imported_count: int
    skipped_count: int
    collection_names: list[str]
    item_titles: list[str]


class KnowledgeImportService:
    SOURCE_FALLBACKS = {
        "docs/poc/channel-risk-register.md": "docs/stories/poc-mvp-run/sprint-0-poc-prep/E0-S2-create-channel-risk-register.md",
        "docs/poc/russian-keyword-library.md": "docs/stories/poc-mvp-run/sprint-0-poc-prep/E0-S3-create-russian-keyword-library.md",
        "docs/poc/faq-and-outreach-templates.md": "docs/stories/poc-mvp-run/sprint-0-poc-prep/E9-S3-create-faq-objection-library.md",
        "docs/poc/ai-output-schema.md": "docs/stories/poc-mvp-run/sprint-1-poc-collection/E2-S1-ai-public-web-extraction.md",
    }
    COLLECTION_DESCRIPTIONS = {
        "channel_sop": "渠道风险、允许动作、禁止动作和人工核查 SOP。",
        "faq": "客服和销售可审核使用的 FAQ。",
        "script_template": "俄语触达模板、禁止承诺点和拒绝联系路径。",
        "keyword_library": "俄罗斯车商、车辆、渠道、地区和排除关键词。",
        "vehicle_knowledge": "车辆采购方向、车型与进口/二手相关知识。",
        "compliance_rules": "合规边界、AI 输出 schema、风险阻断规则。",
        "failed_cases": "Agent 失败案例分类和复盘沉淀。",
    }

    def __init__(self, session: Session) -> None:
        self.session = session
        self.knowledge_service = KnowledgeService(session)

    @staticmethod
    def read_repo_text(repo_root: Path, relative_path: str) -> str:
        path = repo_root / relative_path
        if path.exists():
            return path.read_text(encoding="utf-8")
        fallback_path = repo_root / KnowledgeImportService.SOURCE_FALLBACKS.get(relative_path, "")
        if fallback_path.exists():
            return fallback_path.read_text(encoding="utf-8")
        return path.read_text(encoding="utf-8")

    @classmethod
    def phase_one_import_specs(cls, repo_root: Path | str) -> list[KnowledgeImportSpec]:
        root = Path(repo_root)
        channel_risk = cls.read_repo_text(root, "docs/poc/channel-risk-register.md")
        keywords = cls.read_repo_text(root, "docs/poc/russian-keyword-library.md")
        faq_templates = cls.read_repo_text(root, "docs/poc/faq-and-outreach-templates.md")
        ai_schema = cls.read_repo_text(root, "docs/poc/ai-output-schema.md")
        failed_cases_story = cls.read_repo_text(root, "docs/stories/phase-1-small-run/P1-E4-S5-agent-failed-case-library.md")

        return [
            KnowledgeImportSpec(
                collection_name="channel_sop",
                title="PoC 渠道风险登记与合规 SOP",
                body=channel_risk,
                language="zh",
                country="Russia",
                applicable_channels=["official_website", "public_directory", "search_engine", "maps", "drom", "social_manual"],
                source_ref="docs/poc/channel-risk-register.md",
            ),
            KnowledgeImportSpec(
                collection_name="keyword_library",
                title="俄罗斯车商线索关键词库初版",
                body=keywords,
                language="ru/zh/en",
                country="Russia",
                applicable_channels=["search_engine", "maps", "public_directory", "drom"],
                source_ref="docs/poc/russian-keyword-library.md",
            ),
            KnowledgeImportSpec(
                collection_name="faq",
                title="客服和销售 FAQ 初版",
                body=faq_templates,
                language="zh/ru",
                country="Russia",
                applicable_channels=["manual_outreach", "customer_service", "export_sales"],
                source_ref="docs/poc/faq-and-outreach-templates.md",
            ),
            KnowledgeImportSpec(
                collection_name="script_template",
                title="俄语触达模板与禁止承诺点",
                body=faq_templates,
                language="zh/ru",
                country="Russia",
                applicable_channels=["manual_outreach", "customer_service"],
                source_ref="docs/poc/faq-and-outreach-templates.md",
            ),
            KnowledgeImportSpec(
                collection_name="vehicle_knowledge",
                title="俄罗斯车辆采购关键词与进口二手相关知识",
                body=keywords,
                language="ru/zh/en",
                country="Russia",
                applicable_channels=["lead_extraction", "lead_grading"],
                source_ref="docs/poc/russian-keyword-library.md",
            ),
            KnowledgeImportSpec(
                collection_name="compliance_rules",
                title="AI 输出 schema 与硬规则边界",
                body=ai_schema,
                language="zh",
                country="Russia",
                applicable_channels=["lead_extraction", "lead_grading", "rag"],
                source_ref="docs/poc/ai-output-schema.md",
            ),
            KnowledgeImportSpec(
                collection_name="failed_cases",
                title="Agent 失败案例分类与反馈闭环",
                body=failed_cases_story,
                language="zh",
                country="Russia",
                applicable_channels=["agent_ops", "rag", "retro"],
                source_ref="docs/stories/phase-1-small-run/P1-E4-S5-agent-failed-case-library.md",
            ),
        ]

    @staticmethod
    def import_spec_key(spec: KnowledgeImportSpec) -> str:
        return f"{spec.collection_name}::{spec.title}::{spec.source_ref}"

    def find_existing_item(self, *, collection_id, title: str, source_ref: str) -> KnowledgeItem | None:
        return self.session.scalar(
            select(KnowledgeItem)
            .where(KnowledgeItem.collection_id == collection_id)
            .where(KnowledgeItem.title == title)
            .where(KnowledgeItem.source_ref == source_ref)
        )

    def import_phase_one(self, repo_root: Path | str, *, dry_run: bool = False) -> KnowledgeImportResult:
        specs = self.phase_one_import_specs(repo_root)
        imported_titles: list[str] = []
        skipped_count = 0
        collection_names = sorted({spec.collection_name for spec in specs})
        if dry_run:
            return KnowledgeImportResult(
                imported_count=0,
                skipped_count=0,
                collection_names=collection_names,
                item_titles=[spec.title for spec in specs],
            )

        for spec in specs:
            collection = self.knowledge_service.get_or_create_collection(
                name=spec.collection_name,
                description=self.COLLECTION_DESCRIPTIONS.get(spec.collection_name),
                status=spec.status,
                review_status=spec.review_status,
                version=spec.version,
                source_ref=spec.source_ref,
            )
            existing = self.find_existing_item(
                collection_id=collection.id,
                title=spec.title,
                source_ref=spec.source_ref,
            )
            if existing is not None:
                skipped_count += 1
                continue
            self.knowledge_service.create_item(
                collection_id=collection.id,
                title=spec.title,
                body=spec.body,
                language=spec.language,
                country=spec.country,
                applicable_channels=spec.applicable_channels,
                status=spec.status,
                review_status=spec.review_status,
                source_ref=spec.source_ref,
                version=spec.version,
                metadata_json={"import_key": self.import_spec_key(spec)},
            )
            imported_titles.append(spec.title)
        return KnowledgeImportResult(
            imported_count=len(imported_titles),
            skipped_count=skipped_count,
            collection_names=collection_names,
            item_titles=imported_titles,
        )
