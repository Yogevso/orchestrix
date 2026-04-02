import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.security import hash_password

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite://"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Seed a tenant and user
    db = TestSession()
    tenant = Tenant(id="t-test", name="Test Org", slug="test-org")
    db.add(tenant)
    db.flush()
    user = User(
        id="u-test",
        tenant_id="t-test",
        email="test@test.com",
        password_hash=hash_password("testpass"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    resp = client.post("/auth/login", json={"email": "test@test.com", "password": "testpass"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Health ---

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "uptime_seconds" in data
    assert "total_jobs" in data
    assert "total_events" in data


# --- Auth ---

def test_register_and_login(client):
    resp = client.post("/auth/register", json={
        "email": "new@test.com", "password": "pass123",
        "tenant_slug": "test-org", "role": "viewer",
    })
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@test.com"

    resp = client.post("/auth/login", json={"email": "new@test.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_invalid(client):
    resp = client.post("/auth/login", json={"email": "no@no.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@test.com"


# --- Tenants ---

def test_create_tenant(client):
    resp = client.post("/tenants/", json={"name": "NewOrg", "slug": "new-org"})
    assert resp.status_code == 201


def test_list_tenants_requires_admin(client, auth_headers):
    resp = client.get("/tenants/", headers=auth_headers)
    assert resp.status_code == 200


# --- Jobs ---

@patch("app.api.jobs.celery_app")
def test_create_and_list_jobs(mock_celery, client, auth_headers):
    mock_celery.send_task = MagicMock()

    resp = client.post("/jobs/", json={"type": "analyze_packet_capture", "source": "packet-analyzer"},
                       headers=auth_headers)
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    resp = client.get("/jobs/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    resp = client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["type"] == "analyze_packet_capture"


@patch("app.api.jobs.celery_app")
def test_cancel_job(mock_celery, client, auth_headers):
    mock_celery.send_task = MagicMock()

    resp = client.post("/jobs/", json={"type": "test_job"}, headers=auth_headers)
    job_id = resp.json()["id"]

    resp = client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


# --- Events ---

def test_ingest_and_list_events(client, auth_headers):
    resp = client.post("/events/ingest", json={
        "source": "syswatch", "event_type": "cpu_alert", "severity": "warning",
    }, headers=auth_headers)
    assert resp.status_code == 201

    resp = client.get("/events/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_ingest_invalid_source(client, auth_headers):
    resp = client.post("/events/ingest", json={
        "source": "invalid-source", "event_type": "test",
    }, headers=auth_headers)
    assert resp.status_code == 400


# --- Analytics ---

def test_job_analytics(client, auth_headers):
    resp = client.get("/analytics/jobs", headers=auth_headers)
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_event_analytics(client, auth_headers):
    resp = client.get("/analytics/events", headers=auth_headers)
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_tenant_summary(client, auth_headers):
    resp = client.get("/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["tenant_name"] == "Test Org"


# --- Audit Logs ---

def test_list_audit_logs(client, auth_headers):
    # Login creates an audit log
    resp = client.get("/audit-logs/", headers=auth_headers)
    assert resp.status_code == 200
