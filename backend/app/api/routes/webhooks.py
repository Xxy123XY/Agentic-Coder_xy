from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.api.deps import get_db
from app.db.models import Job, JobStatus
from app.github.webhook import verify_signature, parse_issue_event
from app.api.routes.issues import run_pipeline_background
from app.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Receives GitHub webhook events. Triggers pipeline on new issues."""
    payload_bytes = await request.body()

    # Verify request actually came from GitHub
    if not verify_signature(payload_bytes, x_hub_signature_256):
        logger.warning("invalid_webhook_signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Ignore non-issue events
    if x_github_event != "issues":
        return {"status": "ignored", "reason": f"event {x_github_event} not handled"}

    payload = await request.json()
    issue_info = parse_issue_event(payload)
    if not issue_info:
        return {"status": "ignored", "reason": "not a new issue"}

    # Create job and trigger pipeline
    job = Job(
        id=str(uuid4()),
        repo_full_name=issue_info["repo_full_name"],
        issue_number=issue_info["issue_number"],
        issue_url=issue_info["issue_url"],
        status=JobStatus.RUNNING,
    )
    db.add(job)
    await db.commit()

    initial_state = {
        "job_id": job.id,
        **issue_info,
        "retry_count": 0,
        "events": [],
    }

    background_tasks.add_task(run_pipeline_background, job.id, initial_state)

    return {"status": "ok", "job_id": job.id}