from typing import Any

from fastapi import APIRouter, HTTPException

from app.database import DbSession
from app.models import JobEventModel, JobModel
from app.schema import JobEventPayload

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

@router.post("/events")
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

@router.get("/{job_id}")
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