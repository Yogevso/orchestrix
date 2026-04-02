import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas.job import JobCreate, JobOut, PaginatedResponse
from app.services.audit import create_audit_log
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = Job(
        tenant_id=current_user.tenant_id,
        type=body.type,
        status=JobStatus.PENDING,
        payload=body.payload,
        source=body.source,
        created_by=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue to Celery
    celery_app.send_task("app.workers.tasks.process_job", args=[job.id])

    job.status = JobStatus.QUEUED
    db.commit()
    db.refresh(job)

    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="create",
        resource_type="job",
        resource_id=job.id,
    )
    return job


@router.get("/", response_model=PaginatedResponse[JobOut])
def list_jobs(
    status: str | None = Query(None),
    type: str | None = Query(None),
    source: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Job).filter(Job.tenant_id == current_user.tenant_id)
    if status:
        q = q.filter(Job.status == status)
    if type:
        q = q.filter(Job.type == type)
    if source:
        q = q.filter(Job.source == source)
    total = q.count()
    q = q.order_by(Job.created_at.desc())
    items = q.offset((page - 1) * size).limit(size).all()
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size if total else 0)


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.tenant_id == current_user.tenant_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=JobOut)
def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.tenant_id == current_user.tenant_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.FAILED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed jobs can be retried")

    job.status = JobStatus.QUEUED
    job.retry_count += 1
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    db.commit()

    celery_app.send_task("app.workers.tasks.process_job", args=[job.id])

    db.refresh(job)
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="retry",
        resource_type="job",
        resource_id=job.id,
        details=json.dumps({"retry_count": job.retry_count}),
    )
    return job


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.tenant_id == current_user.tenant_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job cannot be cancelled")

    job.status = JobStatus.CANCELLED
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)

    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="cancel",
        resource_type="job",
        resource_id=job.id,
    )
    return job
