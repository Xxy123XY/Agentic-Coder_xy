from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Any


AgentName = Literal[
    "issue_analyzer",
    "codebase_explorer",
    "fix_drafter",
    "test_writer",
    "validator",
    "pr_creator",
]


class AgentEvent(BaseModel):
    """One event from a running agent — streamed over WebSocket."""
    job_id: str
    agent: AgentName
    event_type: Literal["started", "progress", "completed", "failed", "retry"]
    timestamp: datetime
    message: str
    data: dict[str, Any] = {}


class HumanApprovalRequest(BaseModel):
    """Sent to frontend when pipeline hits the interrupt() gate."""
    job_id: str
    proposed_diff: str
    test_code: str
    validation_passed: bool


class HumanApprovalResponse(BaseModel):
    """Frontend sends back when user clicks Approve or Request Changes."""
    job_id: str
    decision: Literal["approve", "reject"]
    feedback: str | None = None