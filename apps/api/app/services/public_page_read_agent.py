from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import CandidateUrl
from app.models.enums import ChannelRiskLevel, CollectionTaskStatus, PageSnapshotReadStatus
from app.services.audit_risk import AuditRiskLogService
from app.services.failed_cases import FailedCaseService
from app.services.raw_collection import PageSnapshotUpsertResult, RawCollectionService


class _PublicTextParser(HTMLParser):
    IGNORED_TAGS = {"script", "style", "noscript", "svg", "canvas"}

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.IGNORED_TAGS:
            self._ignored_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self.IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if self._ignored_depth == 0 and not self._in_title:
            self.text_parts.append(text)


@dataclass(frozen=True)
class PublicPageSnapshotPayload:
    page_title: str | None
    text_excerpt: str | None
    evidence_note: str
    read_status: PageSnapshotReadStatus
    robots_or_policy_note: str | None


@dataclass(frozen=True)
class PublicPageFetchResult:
    url: str
    html: str
    http_status: int | None
    error_message: str | None = None


@dataclass(frozen=True)
class PublicPageReadResult:
    snapshot_result: PageSnapshotUpsertResult


class PublicPageReadAgentService:
    AGENT_NAME = "public_page_read_agent"
    ACTION = "run_public_page_read"
    DEFAULT_TEXT_EXCERPT_LIMIT = 2000
    HIGH_RISK_TEXT_EXCERPT_LIMIT = 600
    MAX_FETCH_BYTES = 300_000
    ACCESS_WALL_TERMS = (
        "captcha",
        "recaptcha",
        "verify you are human",
        "login required",
        "sign in to continue",
        "access denied",
        "forbidden",
        "доступ запрещ",
        "войдите",
        "авторизуйтесь",
        "капча",
        "проверка безопасности",
    )
    SOCIAL_GRAPH_TERMS = (
        "followers",
        "following",
        "friends",
        "comments",
        "likes",
        "subscribers",
        "подписчик",
        "подписчики",
        "друзья",
        "комментар",
        "лайки",
    )

    def __init__(self, session: Session) -> None:
        self.session = session
        self.raw_collection_service = RawCollectionService(session)
        self.audit_service = AuditRiskLogService(session)
        self.failed_case_service = FailedCaseService(session)

    @classmethod
    def strip_html(cls, html: str) -> tuple[str | None, str]:
        parser = _PublicTextParser()
        parser.feed(html or "")
        title = " ".join(parser.title_parts).strip() or None
        text = "\n".join(parser.text_parts).strip()
        return title, text

    @classmethod
    def contains_access_wall(cls, text: str, *, http_status: int | None = None) -> bool:
        if http_status in {401, 403, 407, 429}:
            return True
        normalized = text.lower()
        return any(term in normalized for term in cls.ACCESS_WALL_TERMS)

    @classmethod
    def remove_social_graph_text(cls, text: str) -> str:
        kept_lines = []
        for line in text.splitlines():
            normalized = line.lower()
            if any(term in normalized for term in cls.SOCIAL_GRAPH_TERMS):
                continue
            kept_lines.append(line)
        return "\n".join(kept_lines)

    @classmethod
    def truncate_excerpt(cls, text: str, *, risk_level: ChannelRiskLevel) -> str:
        limit = cls.HIGH_RISK_TEXT_EXCERPT_LIMIT if risk_level == ChannelRiskLevel.HIGH else cls.DEFAULT_TEXT_EXCERPT_LIMIT
        return text[:limit].strip()

    @classmethod
    def build_snapshot_payload(
        cls,
        *,
        url: str,
        html: str,
        risk_level: str | ChannelRiskLevel,
        http_status: int | None = 200,
        error_message: str | None = None,
    ) -> PublicPageSnapshotPayload:
        risk = ChannelRiskLevel(risk_level)
        if error_message:
            return PublicPageSnapshotPayload(
                page_title=None,
                text_excerpt=None,
                evidence_note="公开页面读取失败，已停止处理。",
                read_status=PageSnapshotReadStatus.FAILED,
                robots_or_policy_note=error_message,
            )

        title, text = cls.strip_html(html)
        if cls.contains_access_wall(f"{title or ''}\n{text}", http_status=http_status):
            return PublicPageSnapshotPayload(
                page_title=title,
                text_excerpt=None,
                evidence_note="检测到验证码、登录墙、访问限制或平台策略墙，已停止读取。",
                read_status=PageSnapshotReadStatus.BLOCKED,
                robots_or_policy_note="不尝试登录或绕过访问限制；不保存受限内容。",
            )
        if http_status is not None and http_status >= 400:
            return PublicPageSnapshotPayload(
                page_title=title,
                text_excerpt=None,
                evidence_note="公开页面返回异常状态码，已停止处理。",
                read_status=PageSnapshotReadStatus.FAILED,
                robots_or_policy_note=f"HTTP {http_status}；未尝试绕过访问限制。",
            )

        public_text = cls.remove_social_graph_text(text) if risk == ChannelRiskLevel.HIGH else text
        excerpt = cls.truncate_excerpt(public_text, risk_level=risk)
        return PublicPageSnapshotPayload(
            page_title=title,
            text_excerpt=excerpt or None,
            evidence_note=f"公开页面读取成功，仅保存文本摘要和有限证据：{url}",
            read_status=PageSnapshotReadStatus.SUCCESS,
            robots_or_policy_note="未登录；未绕过访问限制；未保存完整网页镜像。",
        )

    @classmethod
    def fetch_public_page(cls, url: str) -> PublicPageFetchResult:
        request = Request(
            url,
            headers={
                "User-Agent": "XAgent-PublicPageRead/0.1 (+public summary only; no login; no bypass)",
                "Accept": "text/html, text/plain;q=0.9,*/*;q=0.1",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=8) as response:
                raw = response.read(cls.MAX_FETCH_BYTES)
                charset = response.headers.get_content_charset() or "utf-8"
                return PublicPageFetchResult(
                    url=url,
                    html=raw.decode(charset, errors="replace"),
                    http_status=getattr(response, "status", None),
                )
        except HTTPError as exc:
            body = exc.read(min(cls.MAX_FETCH_BYTES, 50_000)).decode("utf-8", errors="replace")
            return PublicPageFetchResult(url=url, html=body, http_status=exc.code, error_message=None)
        except (URLError, TimeoutError, OSError) as exc:
            return PublicPageFetchResult(url=url, html="", http_status=None, error_message=str(exc))

    @classmethod
    def task_status_after_page_read(
        cls,
        *,
        task_type: str,
        risk_level: str | ChannelRiskLevel,
        read_status: str | PageSnapshotReadStatus,
    ) -> CollectionTaskStatus | None:
        if (
            task_type == RawCollectionService.HIGH_RISK_PUBLIC_DISCOVERY_TASK_TYPE
            and ChannelRiskLevel(risk_level) == ChannelRiskLevel.HIGH
            and PageSnapshotReadStatus(read_status) == PageSnapshotReadStatus.BLOCKED
        ):
            return CollectionTaskStatus.BLOCKED
        return RawCollectionService.task_status_after_snapshot(
            task_type=task_type,
            risk_level=risk_level,
            read_status=read_status,
        )

    def read_candidate_page(
        self,
        *,
        candidate_url_id: UUID,
        public_html: str | None = None,
    ) -> PublicPageReadResult:
        candidate = self.session.get(CandidateUrl, candidate_url_id)
        if candidate is None:
            raise ValueError("candidate URL 不存在。")

        fetched = (
            PublicPageFetchResult(url=candidate.url, html=public_html, http_status=200)
            if public_html is not None
            else self.fetch_public_page(candidate.url)
        )
        payload = self.build_snapshot_payload(
            url=candidate.url,
            html=fetched.html,
            risk_level=candidate.source_risk_level,
            http_status=fetched.http_status,
            error_message=fetched.error_message,
        )
        snapshot_result = self.raw_collection_service.create_page_snapshot(
            candidate_url_id=candidate.id,
            page_title=payload.page_title,
            text_excerpt=payload.text_excerpt,
            evidence_note=payload.evidence_note,
            read_status=payload.read_status,
            robots_or_policy_note=payload.robots_or_policy_note,
        )
        if candidate.task is not None:
            next_status = self.task_status_after_page_read(
                task_type=candidate.task.task_type,
                risk_level=candidate.task.risk_level,
                read_status=payload.read_status,
            )
            if next_status is not None:
                candidate.task.status = next_status
                candidate.task.error_message = "公开页面读取遇到验证码、登录墙或访问策略墙，任务已停止。"
        self.audit_service.record_agent_run(
            task_id=str(candidate.task_id),
            agent_name=self.AGENT_NAME,
            action=self.ACTION,
            input_ref=str(candidate.id),
            output_ref=f"read_status={payload.read_status.value}; snapshot={snapshot_result.page_snapshot.id}",
            result="success" if payload.read_status == PageSnapshotReadStatus.SUCCESS else "blocked",
            error_message=fetched.error_message,
        )
        if payload.read_status == PageSnapshotReadStatus.FAILED:
            self.failed_case_service.record_failed_case(
                case_type=FailedCaseService.classify_failure_reason(payload.robots_or_policy_note or payload.evidence_note),
                source_url=candidate.url,
                risk_level=candidate.source_risk_level,
                related_task_type="public_page_read",
                related_object_type="candidate_url",
                related_object_id=str(candidate.id),
                failure_reason=payload.robots_or_policy_note or payload.evidence_note,
                evidence_note=payload.evidence_note,
                raw_input_ref=str(candidate.id),
                raw_output_json={"read_status": payload.read_status.value},
                model_name=None,
                prompt_version=None,
            )
        return PublicPageReadResult(snapshot_result=snapshot_result)
