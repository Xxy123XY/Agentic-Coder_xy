from pydantic import BaseModel, Field
from typing import Literal


class IssueAnalysis(BaseModel):
    """What IssueAnalyzer agent extracts from a raw GitHub issue."""
    module: str = Field(description="Primary code module affected (e.g. 'auth', 'payments')")
    severity: Literal["low", "medium", "high", "critical"]
    repro_steps: list[str] = Field(description="Steps to reproduce the bug")
    expected_behavior: str
    actual_behavior: str
    keywords: list[str] = Field(description="Keywords for RAG search")


class IssueContext(BaseModel):
    """What gets passed into the pipeline when a new issue arrives."""
    repo_full_name: str
    issue_number: int
    issue_url: str
    title: str
    body: str
    labels: list[str] = []