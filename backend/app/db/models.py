from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone
import enum


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    issue_url = Column(String, nullable=False)
    repo_full_name = Column(String, nullable=False)
    issue_number = Column(Integer, nullable=False)
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, nullable=False)

    # Agent outputs (filled as pipeline progresses)
    issue_analysis = Column(Text, nullable=True)
    relevant_files = Column(Text, nullable=True)
    proposed_diff = Column(Text, nullable=True)
    test_code = Column(Text, nullable=True)
    validation_result = Column(Text, nullable=True)
    pr_url = Column(String, nullable=True)

    # Metadata
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))