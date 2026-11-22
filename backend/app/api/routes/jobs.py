from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.api.deps import get_db
from app.db.models import Job, JobStatus
from app.db.session import async_session
from app.schemas.job import JobSummary, JobDetail
from app.schemas.events import HumanApprovalResponse
from app.graph.builder import compile_graph
from app.graph.checkpointer import get_checkpointer
from app.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    status_filter: JobStatus | None = Query(None, alias="status"),
    limit: int = Query(50, le=100),
):
    query = select(Job).order_by(desc(Job.created_at)).limit(limit)
    if status_filter:
        query = query.where(Job.status == status_filter)
    result = await db.execute(query)
    return [JobSummary.model_validate(j) for j in result.scalars().all()]


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail.model_validate(job)


async def resume_pipeline_background(job_id: str, approved: bool):
    """Background task — resume the paused graph after human decision."""
    final_pr_url: str | None = None
    error_msg: str | None = None

    try:
        async with get_checkpointer() as checkpointer:
            graph = compile_graph(checkpointer)
            config = {"configurable": {"thread_id": job_id}}

            await graph.aupdate_state(config, {"human_approved": approved})
            logger.info("approve_resume_started", job_id=job_id, approved=approved)

            async for event in graph.astream(None, config=config):
                for node, node_output in event.items():
                    if isinstance(node_output, dict):
                        if node_output.get("pr_url"):
                            final_pr_url = node_output["pr_url"]
                        if node_output.get("error_message"):
                            error_msg = node_output["error_message"]
                        logger.info("approve_node_done", job_id=job_id, node=node)

            # Authoritative read from checkpoint after stream completes
            snapshot = await graph.aget_state(config)
            if snapshot and snapshot.values:
                final_pr_url = snapshot.values.get("pr_url") or final_pr_url
                error_msg = snapshot.values.get("error_message") or error_msg

    except Exception as e:
        logger.error("approve_resume_failed", job_id=job_id, error=str(e), exc_info=True)
        error_msg = str(e)

    # Persist final outcome in a fresh DB session (not the request session)
    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        if not approved:
            job.status = JobStatus.FAILED
        elif final_pr_url:
            job.pr_url = final_pr_url
            job.status = JobStatus.COMPLETED
        else:
            job.status = JobStatus.FAILED
            job.error_message = error_msg or "PR creation failed after approval"

        await session.commit()
        logger.info("approve_persisted", job_id=job_id, status=job.status, pr_url=job.pr_url)


@router.post("/{job_id}/approve")
async def approve_job(
    job_id: str,
    decision: HumanApprovalResponse,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused pipeline with human approval decision."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.AWAITING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve job with status: {job.status}",
        )

    # Mark transition immediately so polling clients know something is happening
    job.status = JobStatus.RUNNING
    await db.commit()

    # Resume graph in background — same pattern as initial pipeline run
    background_tasks.add_task(
        resume_pipeline_background,
        job_id,
        decision.decision == "approve",
    )

    return {
        "status": "ok",
        "decision": decision.decision,
        "message": "Pipeline resuming. Poll GET /jobs/{job_id} for final pr_url.",
    }