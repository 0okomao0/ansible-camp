import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# DEFINE HOST
class HostCreate(BaseModel):
    hostname: str
    ipaddr: str
    username: str
    password: str
    environment: str | None = "dev"

class HostResponse(HostCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)

class AnsibleHostVars(BaseModel):
    ansible_host: str
    ansible_user: str
    ansible_password: str
    cmdb_id: str
    environment: str | None = None

class InventoryGroup(BaseModel):
    hosts: dict[str, AnsibleHostVars | dict[str, Any]] = Field(default_factory=dict)
    children: dict[str, Any] = Field(default_factory=dict)

AnsibleInventoryResponse = dict[str, InventoryGroup | Any]



# DEFINE JOB
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

class JobEventResponse(BaseModel):
    status: str
    job_id: str

class JobEventDetailResponse(BaseModel):
    event_type: str
    host: str | None
    task: str | None
    status: str | None
    changed: bool
    msg: str | None
    stdout: str | None
    stderr: str | None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class JobDetailResponse(BaseModel):
    job_id: str
    playbook_name: str | None
    status: str
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
    events: list[JobEventDetailResponse]

    model_config = ConfigDict(from_attributes=True)
