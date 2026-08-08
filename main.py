import datetime
import os
import uuid
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

DATABASE_URL = f'mysql+pymysql://{os.getenv("DB_APP_USER")}:{os.getenv("DB_APP_PASSWORD")}@db:3306/{os.getenv("DB_DATABASE")}'
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define SCHEMA
class HostModel(Base):
    __tablename__ = "hosts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname = Column(String(100), unique=True, nullable=False)
    ipaddr = Column(String(45), nullable=False)
    username = Column(String(45), nullable=False)
    password = Column(String(45), nullable=False)
    environment = Column(String(20), default="dev")  # prod, stg, dev

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    playbook_name = Column(String(100), nullable=True)
    status = Column(String(20), default="RUNNING")  # RUNNING, successful, failed, etc.
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC), onupdate=datetime.datetime.now(datetime.UTC),)
    events = relationship(
        "JobEventModel", back_populates="job", cascade="all, delete-orphan"
    )

class JobEventModel(Base):
    __tablename__ = "job_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # runner_on_ok, runner_on_failed, job_started, job_finished
    host = Column(String(100), nullable=True)
    task = Column(String(255), nullable=True)
    status = Column(String(20), nullable=True)  # OK, FAILED, UNREACHABLE, SKIPPED
    changed = Column(Boolean, default=False, nullable=False)
    msg = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    created_at = Column(DATETIME(fsp=6), default=lambda: datetime.datetime.now(datetime.UTC))
    job = relationship("JobModel", back_populates="events")

class HostCreate(BaseModel):
    hostname: str
    ipaddr: str
    username: str
    password: str
    environment: str | None = "dev"

class HostResponse(HostCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)

class JobEventPayload(BaseModel):
    job_id: str
    event_type: str
    playbook_name: str | None = None
    host: str | None = None
    task: str | None = None
    status: str | None = None
    changed: bool = False
    msg: str | None = None
    stdout: str | None = None
    stderr: str | None = None

# Define Initial
Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
DbSession = Annotated[Session, Depends(get_db)]
app = FastAPI(title="CMDB Host API")


# Define API Endpoint
@app.post("/api/v1/hosts", response_model=HostResponse)
def create_host(host: HostCreate, db: DbSession):
    db_host = HostModel(**host.model_dump())
    db.add(db_host)
    db.commit()
    db.refresh(db_host)
    return db_host

@app.get("/api/v1/hosts", response_model=list[HostResponse])
def read_hosts(db: DbSession):
    return db.query(HostModel).all()

@app.get("/api/v1/inventory")
# no response_model -> Dynamic Inventory
def get_ansible_inventory(db: DbSession) -> dict[str, Any]:
    hosts = db.query(HostModel).all()
    inventory: dict[str, Any] = {
        # "_meta": {"hostvars": {}},
        "all": {"hosts": {}, "children": {}},
    }
    for host in hosts:
        hostname = host.hostname
        inventory["all"]["hosts"][hostname] = {
            "ansible_host": host.ipaddr,
            "ansible_user": host.username,
            "ansible_password": host.password,
            "cmdb_id": host.id,
            "environment": host.environment,}
        env_group = host.environment or "ungrouped"
        if env_group not in inventory["all"]["children"]:
            inventory["all"]["children"][env_group] = {"hosts": {}}
        inventory["all"]["children"][env_group]["hosts"][hostname] = {}
        # inventory["_meta"]["hostvars"][hostname] = {
        # }
    return inventory

@app.post("/api/v1/jobs/events")
def receive_job_event(payload: JobEventPayload, db: DbSession):
    job = db.query(JobModel).filter(JobModel.id == payload.job_id).first()
    if not job:
        job = JobModel(
            id=payload.job_id,
            playbook_name=payload.playbook_name or "unknown",
            status="RUNNING",
        )
        db.add(job)
        db.flush()

    if payload.event_type == "job_finished":
        job.status = payload.status or "FINISHED"
    elif payload.event_type == "job_started":
        job.status = "RUNNING"

    job_event = JobEventModel(
        job_id=payload.job_id,
        event_type=payload.event_type,
        host=payload.host,
        task=payload.task,
        status=payload.status,
        changed=payload.changed,
        msg=payload.msg,
        stdout=payload.stdout,
        stderr=payload.stderr,
    )
    db.add(job_event)
    db.commit()
    return {"status": "success", "job_id": payload.job_id}


@app.get("/api/v1/jobs/{job_id}")
def get_job_detail(job_id: str, db: DbSession) -> dict[str, Any]:
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    events = (
        db.query(JobEventModel)
        .filter(JobEventModel.job_id == job_id)
        .order_by(JobEventModel.created_at.asc())
        .all()
    )

    return {
        "job_id": job.id,
        "playbook_name": job.playbook_name,
        "status": job.status,
        "created_at": job.created_at,
        "events": [
            {
                "event_type": e.event_type,
                "host": e.host,
                "task": e.task,
                "status": e.status,
                "changed": e.changed,
                "msg": e.msg,
                "stdout": e.stdout,
                "stderr": e.stderr,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }