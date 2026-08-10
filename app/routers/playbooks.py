import uuid

from fastapi import APIRouter, HTTPException

from app.database import DbSession
from app.models import PlaybookModel
from app.schema import PlaybookCreate, PlaybookResponse, RecordResponse

router = APIRouter(prefix="/api/v1/playbooks", tags=["playbooks"])

@router.post("/", response_model=RecordResponse)
def create_record(payload: PlaybookCreate, db: DbSession):
    if db.query(PlaybookModel).filter(PlaybookModel.name == payload.name).first():
        raise HTTPException(status_code=409, detail={"status": "failed", "message": "Playbook already exists"})
    
    new_uuid = str(uuid.uuid4())
    playbook = PlaybookModel(
        id = new_uuid,
        name = payload.name,
        description = payload.description or None,
        content = payload.content
    )
    db.add(playbook)
    db.commit()
    db.flush()
    return {"status": "created", "uuid": new_uuid}

@router.get("/", response_model=list[PlaybookResponse])
def get_record(db: DbSession):
    playbooks = db.query(PlaybookModel).all()
    return playbooks

@router.delete("/{uuid}", response_model=RecordResponse)
def delete_record(uuid: str, db: DbSession):
    record = db.query(PlaybookModel).filter(PlaybookModel.id == uuid).first()
    if not record:
        raise HTTPException(status_code=409, detail={"status": "failed", "message": "Playbook not exists"})
    
    db.delete(record)
    db.commit()
    db.flush()
    return  {"status": "deleted", "uuid": uuid}