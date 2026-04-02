from fastapi import FastAPI

from app.api import health, auth, tenants, jobs, events, analytics, audit_logs

app = FastAPI(
    title="Orchestrix",
    description="Multi-tenant backend platform for async job orchestration, telemetry ingestion, and analytics.",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(jobs.router)
app.include_router(events.router)
app.include_router(analytics.router)
app.include_router(audit_logs.router)
