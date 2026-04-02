"""
Seed script — creates sample tenants, users, jobs, and events for local development.

Usage:
    python -m scripts.seed
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.job import Job, JobStatus
from app.models.event import Event
from app.security import hash_password


def seed():
    db = SessionLocal()

    # Tenants
    t1 = Tenant(id="t1", name="Acme Corp", slug="acme")
    t2 = Tenant(id="t2", name="Globex Inc", slug="globex")
    db.add_all([t1, t2])
    db.flush()

    # Users
    admin = User(
        id="u1", tenant_id="t1", email="admin@acme.com",
        password_hash=hash_password("password"), role="admin",
    )
    operator = User(
        id="u2", tenant_id="t1", email="operator@acme.com",
        password_hash=hash_password("password"), role="operator",
    )
    viewer = User(
        id="u3", tenant_id="t2", email="viewer@globex.com",
        password_hash=hash_password("password"), role="viewer",
    )
    db.add_all([admin, operator, viewer])
    db.flush()

    # Jobs
    jobs = [
        Job(tenant_id="t1", type="analyze_packet_capture", status=JobStatus.COMPLETED,
            source="packet-analyzer", created_by="u1"),
        Job(tenant_id="t1", type="run_embedded_validation", status=JobStatus.FAILED,
            source="embedded-tester", created_by="u2", error_message="Timeout"),
        Job(tenant_id="t1", type="ingest_batch_telemetry", status=JobStatus.QUEUED,
            source="syswatch", created_by="u1"),
        Job(tenant_id="t2", type="generate_summary_report", status=JobStatus.PENDING,
            created_by="u3"),
    ]
    db.add_all(jobs)

    # Events
    events = [
        Event(tenant_id="t1", source="syswatch", event_type="cpu_alert",
              severity="warning", payload='{"cpu": 92}'),
        Event(tenant_id="t1", source="packet-analyzer", event_type="anomaly_detected",
              severity="critical", payload='{"type": "port_scan"}'),
        Event(tenant_id="t1", source="embedded-tester", event_type="scenario_failed",
              severity="error", payload='{"scenario": "boot_test"}'),
        Event(tenant_id="t2", source="syswatch", event_type="memory_alert",
              severity="info", payload='{"mem_pct": 78}'),
    ]
    db.add_all(events)

    db.commit()
    db.close()
    print("Seed data created successfully.")


if __name__ == "__main__":
    seed()
