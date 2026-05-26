import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, EntryCreate, EntryORM

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "entries.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_exists(db: Session, content_hash: str) -> bool:
    return (
        db.query(EntryORM).filter(EntryORM.hash == content_hash).first() is not None
    )


def create_entry(db: Session, entry_create: EntryCreate, content_hash: str) -> EntryORM:
    now = entry_create.date_stamp or datetime.now(timezone.utc)
    # Strip timezone for SQLite storage (stored as UTC)
    if hasattr(now, "tzinfo") and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    entry = EntryORM(
        id=str(uuid.uuid4()),
        type=entry_create.type.value,
        content=entry_create.content,
        source=entry_create.source,
        date_stamp=now,
        hash=content_hash,
        tags=entry_create.tags,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_entries(
    db: Session,
    type_filter: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[EntryORM]:
    q = db.query(EntryORM)
    if type_filter:
        q = q.filter(EntryORM.type == type_filter)
    if start_date:
        naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
        q = q.filter(EntryORM.date_stamp >= naive)
    if end_date:
        naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
        q = q.filter(EntryORM.date_stamp <= naive)
    return q.order_by(EntryORM.date_stamp.desc()).all()


def delete_entry(db: Session, entry_id: str) -> bool:
    entry = db.query(EntryORM).filter(EntryORM.id == entry_id).first()
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True
