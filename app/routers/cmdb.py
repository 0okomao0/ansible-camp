import datetime
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.exc import SQLAlchemyError

from app.database import DbSession
from app.models import CMDBModel
from app.schema import (
    ColumnSpec,
    MenuCreate,
    MenuResponse,
    RecordResponse,
    statusResponse,
)

router = APIRouter(prefix="/api/v1/menu", tags=["CMDBManage"])

def _map_type(col: ColumnSpec) -> Column:
    t = col.type.lower()
    if t == "string":
        length = col.length or 255
        return Column(col.rest_name, String(length), nullable=col.nullable)
    if t == "integer":
        return Column(col.rest_name, Integer, nullable=col.nullable)
    if t == "boolean":
        return Column(col.rest_name, Boolean, nullable=col.nullable)
    if t == "datetime":
        return Column(col.rest_name, DateTime, nullable=col.nullable)
    if t == "text":
        return Column(col.rest_name, Text, nullable=col.nullable)
    raise ValueError(f"unsupported column type: {col.type}")

@router.get("/", response_model=list[MenuResponse])
def get_menu_lists(db: DbSession) -> list[CMDBModel]:
    menus = db.query(CMDBModel).all()
    # return [row for row in menus]
    return menus

@router.post("/", response_model=statusResponse)
def create_menu(payload: MenuCreate, db: DbSession):
    if db.query(CMDBModel).filter(CMDBModel.rest_name == payload.rest_name).first():
        raise HTTPException(status_code=409, detail={"status": "failed", "message": "Menu already exists"})

    # For CreateTable
    cols = []
    # For cmdb_define
    cols_define = []
    cols.append(Column("uuid", String(36), primary_key=True, default=lambda: str(uuid.uuid4())))
    cols.append(Column("disabled", Boolean, default=False, nullable=False))
    cols_define.append({"uuid": "SYSTEM"})
    cols_define.append({"disabled": "SYSTEM"})
    for c in payload.columns:
        if c.rest_name in ["uuid", "created_at", "updated_at", "disabled"]:
            # Ignore System Defined Name
            continue
        try:
            cols.append(_map_type(c))
            cols_define.append({c.rest_name: c.type.lower()})
        except ValueError as e:
            raise HTTPException(status_code=400, detail={"status": "failed", "message": str(e)})
    cols.append(Column(
        "created_at", DATETIME(fsp=6), default=lambda: datetime.datetime.now(datetime.UTC)
    ))
    cols.append(Column(
        "updated_at", DATETIME(fsp=6), default=lambda: datetime.datetime.now(datetime.UTC)
    ))
    cols_define.append({"created_at": "SYSTEM"})
    cols_define.append({"updated_at": "SYSTEM"})

    metadata = MetaData()
    table_name = f"CMDB_{str(uuid.uuid4()).upper()}"
    new_table = Table(table_name, metadata, *cols)
    try:
        metadata.create_all(bind=db.get_bind(), tables=[new_table])
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail={"status": "failed", "message": str(e)})
    
    cmdb_define = CMDBModel(
        rest_name = payload.rest_name,
        table_name = table_name,
        columns = cols_define,
    )
    db.add(cmdb_define)
    db.commit()

    return {"status": "created"}

@router.delete("/{rest_name}", response_model=statusResponse)
def drop_menu(rest_name: str, db: DbSession):
    target_define = db.query(CMDBModel).filter(CMDBModel.rest_name == rest_name).first()
    if not target_define:
        raise HTTPException(status_code=404, detail={"status": "failed", "message": "Menu not exists"})
    metadata = MetaData()
    target_table = Table(target_define.table_name, metadata)
    try:
        metadata.drop_all(bind=db.get_bind(), tables=[target_table])
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail={"status": "failed", "message": str(e)})

    db.delete(target_define)
    db.commit()
    return {"status": "dropped"}

@router.get("/{rest_name}/records", response_model=list[dict[str, Any]])
def get_records(rest_name: str, db: DbSession):
    target_define = db.query(CMDBModel).filter(CMDBModel.rest_name == rest_name).first()
    if not target_define:
        raise HTTPException(status_code=404, detail={"status": "failed", "message": "Menu not exists"})
    metadata = MetaData()
    try:
        table = Table(target_define.table_name, metadata, autoload_with=db.get_bind())
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail={"status": "failed", "message": str(e)})
    
    stmt = select(table)
    results = db.execute(stmt).mappings().all()
    
    return [dict(row) for row in results]

@router.post("/{rest_name}/records", response_model=RecordResponse)
def create_record(rest_name: str, payload: dict[str, Any], db: DbSession):
    target_define = db.query(CMDBModel).filter(CMDBModel.rest_name == rest_name).first()
    if not target_define:
        raise HTTPException(status_code=404, detail={"status": "failed", "message": "Menu not exists"})
    metadata = MetaData()
    try:
        table = Table(target_define.table_name, metadata, autoload_with=db.get_bind())
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail={"status": "failed", "message": str(e)})

    # FOR return UUID, beforehand
    new_uuid = str(uuid.uuid4())
    record_data = {**payload, "uuid": new_uuid, "disabled": False, "created_at": datetime.datetime.now(datetime.UTC), "updated_at": datetime.datetime.now(datetime.UTC)}
    try:
        stmt = insert(table).values(**record_data)
        db.execute(stmt)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={"status": "failed", "message": str(e)})

    return {"status": "created", "uuid": new_uuid}

@router.delete("/{rest_name}/records/{uuid}", response_model=RecordResponse)
def delete_record(rest_name: str, uuid: str, db: DbSession):
    target_define = db.query(CMDBModel).filter(CMDBModel.rest_name == rest_name).first()
    if not target_define:
        raise HTTPException(status_code=404, detail={"status": "failed", "message": "Menu not exists"})
    metadata = MetaData()
    try:
        table = Table(target_define.table_name, metadata, autoload_with=db.get_bind())
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail={"status": "failed", "message": str(e)})

    try:
        stmt = delete(table).where(table.c.uuid == uuid)
        result = db.execute(stmt)
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail={"status": "failed", "message": "Record not found"})
            
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={"status": "failed", "message": str(e)})
    
    return {"status": "deleted", "uuid": uuid}
