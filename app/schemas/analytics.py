from pydantic import BaseModel


class AnalyticsJobSummary(BaseModel):
    total: int
    pending: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int
    failure_rate: float
    avg_processing_seconds: float | None


class AnalyticsEventSummary(BaseModel):
    total: int
    by_source: dict[str, int]
    by_type: dict[str, int]
    by_severity: dict[str, int]


class AnalyticsTenantSummary(BaseModel):
    tenant_id: str
    tenant_name: str
    total_jobs: int
    total_events: int
    total_audit_logs: int
