from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.job import Job, JobStatus
from app.models.event import Event
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.analytics import AnalyticsJobSummary, AnalyticsEventSummary, AnalyticsTenantSummary

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/jobs", response_model=AnalyticsJobSummary)
def job_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = db.query(Job).filter(Job.tenant_id == current_user.tenant_id)
    total = base.count()
    counts = {}
    for s in JobStatus:
        counts[s.value] = base.filter(Job.status == s).count()

    failure_rate = (counts["failed"] / total * 100) if total > 0 else 0.0

    avg_seconds = (
        db.query(
            func.avg(func.extract("epoch", Job.finished_at) - func.extract("epoch", Job.started_at))
        )
        .filter(
            Job.tenant_id == current_user.tenant_id,
            Job.status == JobStatus.COMPLETED,
            Job.started_at.isnot(None),
            Job.finished_at.isnot(None),
        )
        .scalar()
    )

    return AnalyticsJobSummary(
        total=total,
        pending=counts["pending"],
        queued=counts["queued"],
        running=counts["running"],
        completed=counts["completed"],
        failed=counts["failed"],
        cancelled=counts["cancelled"],
        failure_rate=round(failure_rate, 2),
        avg_processing_seconds=round(avg_seconds, 3) if avg_seconds else None,
    )


@router.get("/events", response_model=AnalyticsEventSummary)
def event_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = db.query(Event).filter(Event.tenant_id == current_user.tenant_id)
    total = base.count()

    by_source = dict(
        db.query(Event.source, func.count(Event.id))
        .filter(Event.tenant_id == current_user.tenant_id)
        .group_by(Event.source)
        .all()
    )
    by_type = dict(
        db.query(Event.event_type, func.count(Event.id))
        .filter(Event.tenant_id == current_user.tenant_id)
        .group_by(Event.event_type)
        .all()
    )
    by_severity = dict(
        db.query(Event.severity, func.count(Event.id))
        .filter(Event.tenant_id == current_user.tenant_id, Event.severity.isnot(None))
        .group_by(Event.severity)
        .all()
    )

    return AnalyticsEventSummary(total=total, by_source=by_source, by_type=by_type, by_severity=by_severity)


@router.get("/summary", response_model=AnalyticsTenantSummary)
def tenant_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    total_jobs = db.query(Job).filter(Job.tenant_id == current_user.tenant_id).count()
    total_events = db.query(Event).filter(Event.tenant_id == current_user.tenant_id).count()
    total_audit = db.query(AuditLog).filter(AuditLog.tenant_id == current_user.tenant_id).count()

    return AnalyticsTenantSummary(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        total_jobs=total_jobs,
        total_events=total_events,
        total_audit_logs=total_audit,
    )
