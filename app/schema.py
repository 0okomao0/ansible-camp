import datetime
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


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
class JobExecutePayload(BaseModel):
    playbook_id: str

class JobListResponse(BaseModel):
    id: str
    playbook_id: str
    status: str

class JobEventPayload(BaseModel):
    job_id: str
    event_type: str
    playbook_id: str | None = None
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
    playbook_id: str | None
    status: str
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
    events: list[JobEventDetailResponse]

    model_config = ConfigDict(from_attributes=True)



# DEFINE CMDB
class ColumnSpec(BaseModel):
    rest_name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
    type: str = Field(..., description="one of: string, integer, boolean, datetime, text")
    length: int | None
    nullable: bool = True


class MenuCreate(BaseModel):
    rest_name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
    columns: list[ColumnSpec]

class MenuResponse(BaseModel):
    rest_name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
    columns: list[dict[str, str]] 
    model_config = ConfigDict(from_attributes=True)

class statusResponse(BaseModel):
    status: str

class RecordResponse(BaseModel):
    status: str
    uuid: str

# DEFINE PLAYBOOK
class PlaybookCreate(BaseModel):
    name: str
    description: str | None = None
    content: str

    @field_validator("content")
    def validate_yaml(cls, v: str):
        try:
            parsed = yaml.safe_load(v)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML Format: {e}")
        if not isinstance(parsed, (dict, list)):
            # Format Error must be raised as TypeError, But raise Value Error For FastAPI
            raise ValueError("Invalid Playbook Format (Must Be List or Dict)")  # noqa: TRY004
        return v

class PlaybookResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    content: str

class PlaybookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None

    @field_validator("content")
    def validate_yaml(cls, v: str | None):
        if v is None:
            return v
        try:
            parsed = yaml.safe_load(v)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML Format: {e}")
        if not isinstance(parsed, (dict, list)):
            # Format Error must be raised as TypeError, But raise Value Error For FastAPI
            raise ValueError("Invalid Playbook Format (Must Be List or Dict)")  # noqa: TRY004
        return v