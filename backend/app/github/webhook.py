import hmac
import hashlib
from app.config import get_settings
from app.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    if not settings.github_webhook_secret:
        logger.warning("webhook_secret_not_set")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_signature = hmac.new(
        key=settings.github_webhook_secret.encode(),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    received_signature = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected_signature, received_signature)


def parse_issue_event(payload: dict) -> dict | None:
    action = payload.get("action")

    if action != "opened":
        return None

    issue = payload.get("issue", {})
    repo = payload.get("repository", {})

    return {
        "repo_full_name": repo.get("full_name"),
        "issue_number": issue.get("number"),
        "issue_url": issue.get("html_url"),
        "issue_title": issue.get("title", ""),
        "issue_body": issue.get("body", "") or "",
        "labels": [l.get("name") for l in issue.get("labels", [])],
    }