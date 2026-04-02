import time
import traceback
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.job import Job, JobStatus


@celery_app.task(name="app.workers.tasks.process_job", bind=True, max_retries=3)
def process_job(self, job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"error": "Job not found"}

        if job.status == JobStatus.CANCELLED:
            return {"status": "cancelled"}

        # Mark as running
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        # --- Simulate job processing based on type ---
        _execute_job(job)

        # Mark as completed
        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(timezone.utc)
            job.error_message = str(exc)[:1000]
            db.commit()
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


def _execute_job(job: Job):
    """Simulate processing for different job types."""
    job_type = job.type.lower()

    if job_type == "analyze_packet_capture":
        time.sleep(2)
    elif job_type == "run_embedded_validation":
        time.sleep(3)
    elif job_type == "ingest_batch_telemetry":
        time.sleep(1)
    elif job_type == "generate_summary_report":
        time.sleep(2)
    else:
        time.sleep(1)
