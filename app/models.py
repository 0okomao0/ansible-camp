import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import relationship

from app.database import Base


class HostModel(Base):
    __tablename__ = "hosts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname = Column(String(100), unique=True, nullable=False)
    ipaddr = Column(String(45), nullable=False)
    username = Column(String(45), nullable=False)
    password = Column(String(45), nullable=False)
    environment = Column(String(20), default="dev")

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    playbook_name = Column(String(100), nullable=True)
    status = Column(String(20), default="RUNNING")
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    updated_at = Column(
        DateTime,
        default=datetime.datetime.now(datetime.UTC),
        onupdate=datetime.datetime.now(datetime.UTC),
    )
    events = relationship(
        "JobEventModel", back_populates="job", cascade="all, delete-orphan"
    )

class JobEventModel(Base):
    __tablename__ = "job_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    host = Column(String(100), nullable=True)
    task = Column(String(255), nullable=True)
    status = Column(String(20), nullable=True)
    changed = Column(Boolean, default=False, nullable=False)
    msg = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    created_at = Column(
        DATETIME(fsp=6), default=lambda: datetime.datetime.now(datetime.UTC)
    )
    job = relationship("JobModel", back_populates="events")