from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase


class EntryType(str, Enum):
    file = "file"
    email = "email"
    text = "text"


class Base(DeclarativeBase):
    pass


class EntryORM(Base):
    __tablename__ = "entries"

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    date_stamp = Column(DateTime, nullable=False)
    hash = Column(String, nullable=False, unique=True)
    tags = Column(JSON, nullable=True)


class EntryCreate(BaseModel):
    type: EntryType
    content: str
    source: str
    date_stamp: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)


class EntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    content: str
    source: str
    date_stamp: datetime
    hash: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v):
        return v or []
