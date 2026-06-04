from pathlib import Path

from app.models.enums import ChannelRiskLevel, PageSnapshotReadStatus
from app.services.public_page_read_agent import PublicPageReadAgentService


API_ROOT = Path(__file__).resolve().parents[1]


def test_public_html_extracts_title_excerpt_and_evidence_without_full_page_mirror() -> None:
    html = """
    <html>
      <head><title>Auto City Moscow</title><script>secret()</script></head>
      <body>
        <h1>Auto City Moscow</h1>
        <p>Official dealer of used cars from China.</p>
        <p>Email: sales@example.ru Phone: +7 900 000 00 00</p>
      </body>
    </html>
    """

    snapshot = PublicPageReadAgentService.build_snapshot_payload(
        url="https://example.ru",
        html=html,
        risk_level=ChannelRiskLevel.MEDIUM,
    )

    assert snapshot.page_title == "Auto City Moscow"
    assert snapshot.read_status == PageSnapshotReadStatus.SUCCESS
    assert "Official dealer" in snapshot.text_excerpt
    assert "secret()" not in snapshot.text_excerpt
    assert "公开页面读取成功" in snapshot.evidence_note
    assert len(snapshot.text_excerpt) <= PublicPageReadAgentService.DEFAULT_TEXT_EXCERPT_LIMIT


def test_captcha_or_login_wall_is_recorded_as_blocked_without_bypass() -> None:
    for html in ("Please complete CAPTCHA to continue", "Login required to view this page"):
        snapshot = PublicPageReadAgentService.build_snapshot_payload(
            url="https://example.ru/private",
            html=html,
            risk_level=ChannelRiskLevel.MEDIUM,
        )

        assert snapshot.read_status == PageSnapshotReadStatus.BLOCKED
        assert "不尝试登录或绕过访问限制" in (snapshot.robots_or_policy_note or "")


def test_http_error_without_access_wall_is_recorded_as_failed() -> None:
    snapshot = PublicPageReadAgentService.build_snapshot_payload(
        url="https://example.ru/missing",
        html="Not Found",
        risk_level=ChannelRiskLevel.MEDIUM,
        http_status=404,
    )

    assert snapshot.read_status == PageSnapshotReadStatus.FAILED
    assert snapshot.text_excerpt is None
    assert "HTTP 404" in (snapshot.robots_or_policy_note or "")


def test_high_risk_page_keeps_limited_business_evidence_and_drops_social_graph_text() -> None:
    html = """
    <html><head><title>VK Auto Dealer</title></head><body>
      <p>Business contact: WhatsApp +7 900 111 22 33</p>
      <p>Followers: 12000</p>
      <p>Friends: 300</p>
      <p>Comments from users should not be stored.</p>
      <p>Email: sales@dealer.ru</p>
    </body></html>
    """

    snapshot = PublicPageReadAgentService.build_snapshot_payload(
        url="https://vk.example/dealer",
        html=html,
        risk_level=ChannelRiskLevel.HIGH,
    )

    assert snapshot.read_status == PageSnapshotReadStatus.SUCCESS
    assert "WhatsApp" in snapshot.text_excerpt
    assert "sales@dealer.ru" in snapshot.text_excerpt
    assert "Followers" not in snapshot.text_excerpt
    assert "Friends" not in snapshot.text_excerpt
    assert "Comments" not in snapshot.text_excerpt
    assert len(snapshot.text_excerpt) <= PublicPageReadAgentService.HIGH_RISK_TEXT_EXCERPT_LIMIT


def test_high_risk_blocked_snapshot_blocks_high_risk_collection_task() -> None:
    assert (
        PublicPageReadAgentService.task_status_after_page_read(
            task_type="high_risk_public_discovery",
            risk_level=ChannelRiskLevel.HIGH,
            read_status=PageSnapshotReadStatus.BLOCKED,
        )
        == "blocked"
    )


def test_public_page_read_api_contract_is_registered() -> None:
    main_py = (API_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    api_file = API_ROOT / "app" / "api" / "public_page_read.py"

    assert api_file.exists()
    assert "public_page_read_router" in main_py
    assert '@router.post("/run"' in api_file.read_text(encoding="utf-8")
