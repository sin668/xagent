FORBIDDEN_SEARCH_ACTION_TERMS = {
    "auto_dm",
    "friend_request",
    "join_group",
    "login_collection",
    "anti_scraping_bypass",
}


def validate_public_search_actions(requested_actions: list[str]) -> None:
    normalized = {str(item).strip().lower() for item in requested_actions}
    if normalized & FORBIDDEN_SEARCH_ACTION_TERMS:
        raise ValueError("不允许自动私信、加好友、登录采集或反爬规避。")


class EmptyPublicSearchTool:
    def search(self, keywords: list[str]) -> list[dict]:
        return []
