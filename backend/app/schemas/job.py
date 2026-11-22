from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.db.models import JobStatus


class JobBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    issue_url: str
    repo_full_name: str
    issue_number: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime


class JobSummary(JobBase):
    """Minimal job info for the /jobs list endpoint."""
    pr_url: str | None = None
    retry_count: int = 0


class JobDetail(JobBase):
    """Full job info for the /jobs/{id} endpoint."""
    issue_analysis: str | None = None
    relevant_files: str | None = None
    proposed_diff: str | None = None
    test_code: str | None = None
    validation_result: str | None = None
    pr_url: str | None = None
    retry_count: int = 0
    error_message: str | None = None


class JobCreateRequest(BaseModel):
    """POST /issues/{id}/solve body."""
    repo_full_name: str
    issue_number: int