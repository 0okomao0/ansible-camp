import datetime
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.database import DbSession
from app.models import JobEventModel, JobModel, PlaybookModel
from app.schema import (
    JobDetailResponse,
    JobEventPayload,
    JobEventResponse,
    JobExecutePayload,
    JobListResponse,
)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

@router.post("/execute", response_model=JobEventResponse)
def execute_job(payload: JobExecutePayload, db: DbSession):
    playbook = db.query(PlaybookModel).filter(PlaybookModel.id == payload.playbook_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail={"status": "failed", "message": "Playbook not exists"})
    
    new_uuid = str(uuid.uuid4())
    job = JobModel(
        id = new_uuid,
        playbook_id = playbook.id,
        status="NOTEXECUTED",
        created_at = datetime.datetime.now(datetime.UTC)
    )
    db.add(job)
    db.commit()
    db.flush()
    return {"status": "success", "job_id": new_uuid}

@router.get("/", response_model=list[JobListResponse])
def get_jobs(db: DbSession):
    jobs = db.query(JobModel).all()
    return jobs

@router.get("/ne", response_model=list[JobListResponse])
def get_jobs_not_executed(db: DbSession, job_count: int | None = None):
    query = db.query(JobModel).filter(JobModel.status == "NOTEXECUTED").order_by(JobModel.created_at.asc())
    if job_count is not None:
        query = query.limit(job_count)
    jobs = query.all()
    for job in jobs:
        job.status = "PENDING"
    db.commit()
    return jobs

@router.post("/events", response_model=JobEventResponse)
def receive_job_event(payload: JobEventPayload, db: DbSession):
    job = db.query(JobModel).filter(JobModel.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    payload.status = payload.status.upper()
    if payload.event_type == "job_started":
        job.status = payload.status
        if job.started_at is None:
            job.started_at = datetime.datetime.now(datetime.UTC)
    elif payload.event_type == "job_prepare_started":
        job.started_at = datetime.datetime.now(datetime.UTC)
    elif payload.event_type == "job_finished":
        job.status = payload.status
        job.ended_at = datetime.datetime.now(datetime.UTC)
    elif payload.event_type == "job_prepare_finished":
        job.status = payload.status
        if payload.status == "FAILED":
            job.ended_at = datetime.datetime.now(datetime.UTC)

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

@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: str, db: DbSession) -> dict[str, Any]:
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobDetailResponse(
            job_id=job.id,
            playbook_id=job.playbook_id,
            status=job.status,
            started_at=job.started_at,
            ended_at=job.ended_at,
            created_at=job.created_at,
            events=sorted(job.events, key=lambda e: e.created_at),
        )