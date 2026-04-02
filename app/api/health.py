import time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job, JobStatus
from app.models.event import Event
from app.models.user import User

router = APIRouter(tags=["Health"])

_start_time = time.time()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    uptime = round(time.time() - _start_time, 2)
    total_jobs = db.query(func.count(Job.id)).scalar()
    jobs_by_status = dict(
        db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    )
    total_events = db.query(func.count(Event.id)).scalar()
    total_users = db.query(func.count(User.id)).scalar()
    return {
        "uptime_seconds": uptime,
        "total_jobs": total_jobs,
        "jobs_by_status": jobs_by_status,
        "total_events": total_events,
        "total_users": total_users,
    }
