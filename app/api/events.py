from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventIngest, EventOut
from app.schemas.job import PaginatedResponse

router = APIRouter(prefix="/events", tags=["Events"])

VALID_SOURCES = {"syswatch", "packet-analyzer", "embedded-tester"}


@router.post("/ingest", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def ingest_event(
    body: EventIngest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.source not in VALID_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source. Must be one of: {', '.join(sorted(VALID_SOURCES))}",
        )
    event = Event(
        tenant_id=current_user.tenant_id,
        source=body.source,
        batch_id=body.batch_id,
        event_type=body.event_type,
        severity=body.severity,
        payload=body.payload,
        timestamp=body.timestamp,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=PaginatedResponse[EventOut])
def list_events(
    source: str | None = Query(None),
    event_type: str | None = Query(None),
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Event).filter(Event.tenant_id == current_user.tenant_id)
    if source:
        q = q.filter(Event.source == source)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if severity:
        q = q.filter(Event.severity == severity)
    total = q.count()
    q = q.order_by(Event.created_at.desc())
    items = q.offset((page - 1) * size).limit(size).all()
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size if total else 0)


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id, Event.tenant_id == current_user.tenant_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event
