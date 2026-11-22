# from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from uuid import uuid4
# from app.api.deps import get_db
# from app.db.models import Job, JobStatus
# from app.schemas.job import JobCreateRequest, JobDetail
# from app.github.client import get_issue
# from app.graph.builder import compile_graph
# from app.graph.checkpointer import get_checkpointer
# from app.observability.logger import get_logger

# logger = get_logger(__name__)
# router = APIRouter(prefix="/issues", tags=["issues"])


# async def run_pipeline_background(job_id: str, initial_state: dict):
#     """Background task that actually runs the LangGraph pipeline."""
#     async with get_checkpointer() as checkpointer:
#         graph = compile_graph(checkpointer)
#         config = {"configurable": {"thread_id": job_id}}

#         try:
#             async for event in graph.astream(initial_state, config=config):
#                 # logger.info("graph_event", job_id=job_id, event=list(event.keys()))
#                 logger.info("graph_event", job_id=job_id, event=list(event.keys()))
#         except Exception as e:
#             # logger.error("pipeline_failed", job_id=job_id, error=str(e))
#             logger.info("graph_event", job_id=job_id, nodes=list(event.keys()))


# @router.post("/solve", response_model=JobDetail)
# async def solve_issue(
#     request: JobCreateRequest,
#     background_tasks: BackgroundTasks,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Trigger the pipeline for a specific GitHub issue."""
#     # Fetch issue from GitHub to get title + body
#     try:
#         issue = get_issue(request.repo_full_name, request.issue_number)
#     except Exception as e:
#         raise HTTPException(status_code=404, detail=f"Issue not found: {e}")

#     # Create job record in database
#     job = Job(
#         id=str(uuid4()),
#         repo_full_name=request.repo_full_name,
#         issue_number=request.issue_number,
#         issue_url=issue.html_url,
#         status=JobStatus.RUNNING,
#     )
#     db.add(job)
#     await db.commit()
#     await db.refresh(job)

#     # Build initial state for the graph
#     initial_state = {
#         "job_id": job.id,
#         "repo_full_name": request.repo_full_name,
#         "issue_number": request.issue_number,
#         "issue_url": issue.html_url,
#         "issue_title": issue.title,
#         "issue_body": issue.body or "",
#         "retry_count": 0,
#         "events": [],
#     }

#     # Launch pipeline in background — return immediately
#     background_tasks.add_task(run_pipeline_background, job.id, initial_state)

#     return JobDetail.model_validate(job)

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from app.api.deps import get_db
from app.db.models import Job, JobStatus
from app.db.session import async_session
from app.schemas.job import JobCreateRequest, JobDetail
from app.github.client import get_issue
from app.graph.builder import compile_graph
from app.graph.checkpointer import get_checkpointer
from app.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/issues", tags=["issues"])


async def _update_job(job_id: str, status: JobStatus, **kwargs) -> None:
    """Update job record in DB."""
    async with async_session() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
        job.status = status
        for key, value in kwargs.items():
            if value is not None and hasattr(job, key):
                setattr(job, key, value)
        await db.commit()


async def run_pipeline_background(job_id: str, initial_state: dict):
    """Background task that runs the LangGraph pipeline."""
    async with get_checkpointer() as checkpointer:
        graph = compile_graph(checkpointer)
        config = {"configurable": {"thread_id": job_id}}

        try:
            async for event in graph.astream(initial_state, config=config):
                logger.info("graph_event", job_id=job_id, nodes=list(event.keys()))
        except Exception as e:
            logger.error("pipeline_failed", job_id=job_id, error=str(e))
            await _update_job(job_id, JobStatus.FAILED, error_message=str(e))
            return

        # Check if graph paused at interrupt or fully completed
        state = await graph.aget_state(config)

        if state.next:
            # Paused at human_review interrupt
            logger.info("pipeline_awaiting_review", job_id=job_id)
            await _update_job(
                job_id,
                JobStatus.AWAITING_REVIEW,
                proposed_diff=state.values.get("proposed_diff"),
                test_code=state.values.get("test_code"),
            )
        else:
            # Fully completed
            pr_url = state.values.get("pr_url")
            logger.info("pipeline_completed", job_id=job_id, pr_url=pr_url)
            await _update_job(
                job_id,
                JobStatus.COMPLETED,
                pr_url=pr_url,
            )


@router.post("/solve", response_model=JobDetail)
async def solve_issue(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger the pipeline for a specific GitHub issue."""
    try:
        issue = get_issue(request.repo_full_name, request.issue_number)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Issue not found: {e}")

    job = Job(
        id=str(uuid4()),
        repo_full_name=request.repo_full_name,
        issue_number=request.issue_number,
        issue_url=issue.html_url,
        status=JobStatus.RUNNING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    initial_state = {
        "job_id": job.id,
        "repo_full_name": request.repo_full_name,
        "issue_number": request.issue_number,
        "issue_url": issue.html_url,
        "issue_title": issue.title,
        "issue_body": issue.body or "",
        "retry_count": 0,
        "events": [],
    }

    background_tasks.add_task(run_pipeline_background, job.id, initial_state)
    return JobDetail.model_validate(job)