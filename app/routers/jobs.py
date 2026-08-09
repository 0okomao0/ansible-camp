import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from app.database import DbSession
from app.models import JobEventModel, JobModel
from app.schema import JobDetailResponse, JobEventPayload, JobEventResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

@router.post("/events", response_model=JobEventResponse)
def receive_job_event(payload: JobEventPayload, db: DbSession):
    job = db.query(JobModel).filter(JobModel.id == payload.job_id).first()
    if not job:
        job = JobModel(
            id=payload.job_id,
            playbook_name=payload.playbook_name or "unknown",
            status="PREPARING",
            created_at = datetime.datetime.now(datetime.UTC)
        )
        db.add(job)
        db.flush()

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
            playbook_name=job.playbook_name,
            status=job.status,
            started_at=job.started_at,
            ended_at=job.ended_at,
            created_at=job.created_at,
            events=sorted(job.events, key=lambda e: e.created_at),
        )