import uuid

from fastapi import APIRouter, HTTPException

from app.database import DbSession
from app.models import PlaybookModel
from app.schema import PlaybookCreate, PlaybookResponse, PlaybookUpdate, RecordResponse

router = APIRouter(prefix="/api/v1/playbooks", tags=["playbooks"])

@router.get("/", response_model=list[PlaybookResponse])
def get_playbooks(db: DbSession):
    playbooks = db.query(PlaybookModel).all()
    return playbooks

@router.post("/", response_model=RecordResponse)
def create_playbook(payload: PlaybookCreate, db: DbSession):
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

@router.delete("/{uuid}", response_model=RecordResponse)
def delete_playbook(uuid: str, db: DbSession):
    playbook = db.query(PlaybookModel).filter(PlaybookModel.id == uuid).first()
    if not playbook:
        raise HTTPException(status_code=409, detail={"status": "failed", "message": "Playbook not exists"})
    
    db.delete(playbook)
    db.commit()
    db.flush()
    return  {"status": "deleted", "uuid": uuid}

@router.patch("/{uuid}", response_model=RecordResponse)
def update_playbook(uuid: str, payload: PlaybookUpdate, db: DbSession):
    playbook = db.query(PlaybookModel).filter(PlaybookModel.id == uuid).first()
    if not playbook:
        raise HTTPException(status_code=404, detail={"status": "failed", "message": "Playbook not exists"})

    update_data = payload.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if not field in ["id", "created_at", "updated_at"]:
            setattr(playbook, field, value)

    db.commit()
    db.refresh(playbook)
    return {"status": "Updated", "uuid": uuid}