from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FeishuRecord:
    record_id: str
    fields: dict[str, object]


class FeishuClient(Protocol):
    def list_records(self, table_name: str) -> list[FeishuRecord]:
        """Return records from a Feishu Bitable table without mutating Feishu."""


class FeishuApiClient:
    def __init__(self, app_id: str | None, app_secret: str | None, bitable_app_token: str | None = None) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.bitable_app_token = bitable_app_token

    def list_records(self, table_name: str) -> list[FeishuRecord]:
        if not self.app_id or not self.app_secret or not self.bitable_app_token:
            raise RuntimeError("Feishu credentials are not configured.")
        raise NotImplementedError("Real Feishu API integration will be implemented after app permissions are available.")

