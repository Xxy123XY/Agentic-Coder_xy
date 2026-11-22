from typing import Literal
from app.config import get_settings

settings = get_settings()


def route_after_validator(state: dict) -> Literal["sandbox", "retry", "fail"]:
    """Decide what happens after Validator runs."""
    if not state.get("validation_passed", False):
        if state.get("retry_count", 0) < settings.max_retries:
            return "retry"
        return "fail"
    return "sandbox"


def route_after_sandbox(state: dict) -> Literal["human_review", "retry", "fail"]:
    """Decide what happens after sandbox test execution."""
    if state.get("tests_passed", False):
        return "human_review"

    if state.get("retry_count", 0) < settings.max_retries:
        return "retry"
    return "fail"


def route_after_human(state: dict) -> Literal["pr_creator", "end"]:
    """Decide what happens after human approval decision."""
    if state.get("human_approved", False):
        return "pr_creator"
    return "end"


def increment_retry(state: dict) -> dict:
    """Called between fix attempts — bumps the retry counter."""
    return {"retry_count": state.get("retry_count", 0) + 1}