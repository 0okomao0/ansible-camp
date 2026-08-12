from typing import Any

from fastapi import APIRouter

from app.database import DbSession
from app.models import HostModel
from app.schema import AnsibleInventoryResponse, HostCreate, HostResponse

router = APIRouter(prefix="/api/v1", tags=["hosts"])

@router.post("/hosts", response_model=HostResponse)
def create_host(host: HostCreate, db: DbSession):
    db_host = HostModel(**host.model_dump())
    db.add(db_host)
    db.commit()
    db.refresh(db_host)
    return db_host

@router.get("/hosts", response_model=list[HostResponse])
def get_hosts(db: DbSession):
    return db.query(HostModel).all()

@router.get("/inventory", response_model=AnsibleInventoryResponse)
def get_hosts_for_ansible_inventory(db: DbSession) -> dict[str, Any]:
    hosts = db.query(HostModel).all()
    inventory: dict[str, Any] = {
        "all": {"hosts": {}, "children": {}},
    }
    for host in hosts:
        hostname = host.hostname
        inventory["all"]["hosts"][hostname] = {
            "ansible_host": host.ipaddr,
            "ansible_user": host.username,
            "ansible_password": host.password,
            "cmdb_id": host.id,
            "environment": host.environment,
        }
        env_group = host.environment or "ungrouped"
        if env_group not in inventory["all"]["children"]:
            inventory["all"]["children"][env_group] = {"hosts": {}}
        inventory["all"]["children"][env_group]["hosts"][hostname] = {}
    return inventory