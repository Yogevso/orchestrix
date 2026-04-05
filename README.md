# Orchestrix

> **Part of the [Orchestrix Platform](https://github.com/Yogevso/Orchestrix-Platform)** — the multi-tenant backend for job orchestration and telemetry ingestion.

> A production-style backend platform for orchestrating async workflows, ingesting telemetry from system tools, and analyzing operational data across tenants.

Multi-tenant backend platform for async job orchestration, telemetry ingestion, and analytics.

## Why This Exists

Modern systems rely on multiple tools that generate data and require orchestration — monitoring tools, analyzers, and test frameworks.

Orchestrix provides a unified backend layer to:
- orchestrate long-running workflows
- ingest telemetry from distributed sources
- persist and analyze operational data
- expose a clean API for querying system behavior

It transforms standalone tools into a coordinated platform.

## Key Highlights

- Multi-tenant backend with RBAC and tenant isolation
- Async job processing with Celery + Redis
- Unified ingestion pipeline for multiple system tools
- Full audit logging of user and system actions
- Analytics endpoints for operational insights
- Production-style architecture (API + DB + worker + queue)

## Architecture

```
SysWatch ───────────────┐
Packet Analyzer ────────┼──→ FastAPI API → PostgreSQL → Analytics
Embedded Tester ────────┘         │
                                  ↓
                             Redis + Celery
                                  ↓
                                Worker
```

## End-to-End Flow

1. **SysWatch** collects system metrics and sends events to `/events/ingest`
2. **Packet Analyzer** submits anomaly detection jobs to `/jobs`
3. **Embedded Tester** creates validation jobs and reports outcomes
4. Orchestrix enqueues jobs via Redis and processes them asynchronously
5. Results, events, and audit logs are stored in PostgreSQL
6. Clients and dashboards query `/analytics` and `/jobs` for insights

## Design Decisions

- **FastAPI** for typed APIs, validation, and auto-generated docs
- **PostgreSQL** for relational integrity and analytical queries
- **Celery + Redis** for reliable async job processing and retries
- **SQLAlchemy 2.0** for explicit and modern ORM patterns
- **Tenant-scoped architecture** to ensure data isolation

## API Design Principles

- Resource-oriented endpoints (`/jobs`, `/events`, `/analytics`)
- Consistent filtering and pagination across list endpoints
- Tenant-scoped access enforced at the API layer
- Separation between ingestion (`POST`) and querying (`GET`)
- Clear lifecycle modeling for async jobs

## Error Handling

- Validation errors return `422` with detailed messages
- Unauthorized access returns `401` / `403`
- Failed jobs include error messages and retry history
- Consistent JSON response structure across endpoints

## Tech Stack

- **FastAPI** — REST API framework
- **PostgreSQL** — primary datastore
- **SQLAlchemy 2.0** — ORM with mapped columns
- **Alembic** — database migrations
- **Celery + Redis** — async task queue
- **Pydantic v2** — request/response validation
- **Docker Compose** — local development environment

## Quick Start

```bash
# Start all services
docker compose up --build

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Run Migrations & Seed Data

```bash
# Migrations run automatically on startup
# To seed sample data:
docker compose exec api python -m scripts.seed
```

### Run Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Demo Flow

```bash
# 1. Create a tenant
curl -X POST http://localhost:8000/tenants/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "slug": "acme"}'

# 2. Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acme.com", "password": "secret123", "tenant_slug": "acme", "role": "admin"}'

# 3. Login and get JWT
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acme.com", "password": "secret123"}' | jq -r .access_token)

# 4. Create an async job (processed by Celery worker)
curl -X POST http://localhost:8000/jobs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "analyze_packet_capture", "source": "packet-analyzer", "payload": "{\"file\": \"capture.pcap\"}"}'

# 5. Ingest telemetry events
curl -X POST http://localhost:8000/events/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "syswatch", "event_type": "cpu_alert", "severity": "warning", "payload": "{\"cpu\": 92}"}'

# 6. Query analytics
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analytics/jobs
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analytics/events
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analytics/summary

# 7. View audit trail
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/audit-logs/

# 8. Check system metrics
curl http://localhost:8000/metrics
```

### Sample Responses

**Job Analytics** — `GET /analytics/jobs`
```json
{
  "total": 2,
  "pending": 0,
  "queued": 0,
  "running": 0,
  "completed": 2,
  "failed": 0,
  "cancelled": 0,
  "failure_rate": 0.0,
  "avg_processing_seconds": 2.009
}
```

**Event Analytics** — `GET /analytics/events`
```json
{
  "total": 6,
  "by_source": {"syswatch": 2, "packet-analyzer": 2, "embedded-tester": 2},
  "by_type": {"cpu_alert": 2, "anomaly_detected": 2, "scenario_failed": 2},
  "by_severity": {"warning": 2, "critical": 2, "error": 2}
}
```

**Tenant Summary** — `GET /analytics/summary`
```json
{
  "tenant_id": "3b8ad5ac-...",
  "tenant_name": "TestOrg",
  "total_jobs": 2,
  "total_events": 6,
  "total_audit_logs": 6
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/auth/register` | Register user |
| POST | `/auth/login` | Login, get JWT |
| GET | `/auth/me` | Current user |
| POST | `/tenants/` | Create tenant |
| GET | `/tenants/` | List tenants (admin) |
| POST | `/jobs/` | Create async job |
| GET | `/jobs/` | List jobs (filtered) |
| GET | `/jobs/{id}` | Get job details |
| POST | `/jobs/{id}/retry` | Retry failed job |
| POST | `/jobs/{id}/cancel` | Cancel job |
| POST | `/events/ingest` | Ingest telemetry event |
| GET | `/events/` | List events |
| GET | `/events/{id}` | Get event details |
| GET | `/analytics/jobs` | Job analytics |
| GET | `/analytics/events` | Event analytics |
| GET | `/analytics/summary` | Tenant summary |
| GET | `/audit-logs/` | Audit log history |
| GET | `/metrics` | System metrics |

## Project Structure

```
orchestrix/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py             # Settings from environment
│   ├── database.py           # SQLAlchemy engine & session
│   ├── security.py           # JWT & password hashing
│   ├── dependencies.py       # Auth dependencies
│   ├── api/                  # Route handlers
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── tenants.py
│   │   ├── jobs.py
│   │   ├── events.py
│   │   ├── analytics.py
│   │   └── audit_logs.py
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   └── workers/              # Celery tasks
│       ├── celery_app.py
│       └── tasks.py
├── migrations/               # Alembic migrations
├── tests/                    # pytest test suite
├── scripts/                  # Seed & utility scripts
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Multi-Tenancy & Roles

- **Tenants** isolate all data (jobs, events, audit logs)
- **Roles**: `admin`, `operator`, `viewer`
- JWT tokens carry `tenant_id` — all queries are tenant-scoped

## Real-World Scenario

A production system experiences high latency and increasing connection counts.

- **SysWatch** detects CPU spikes and sends alerts
- **Packet Analyzer** submits a job to analyze suspicious traffic
- Orchestrix processes the job asynchronously
- Events and results are stored and correlated
- Engineers query `/analytics/summary` to identify patterns
- Audit logs reveal repeated job retries and failures

This enables faster debugging and system diagnosis across tools.

## Integration Points

| Tool | Integration |
|------|-------------|
| **SysWatch** | Push resource/alert events via `/events/ingest` |
| **Packet Analyzer** | Submit analysis jobs or send anomaly events |
| **Embedded Tester** | Create validation jobs, post test run outcomes |

## Future Work

- Rate limiting for ingestion endpoints
- Horizontal scaling of workers
- Real-time updates via WebSocket
- Event streaming (Kafka)

## License

MIT
