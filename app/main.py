from fastapi import FastAPI

from app.database import Base, engine
from app.routers import cmdb, hosts, jobs, playbooks

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CMDB & Ansible Jobs API")

app.include_router(hosts.router)
app.include_router(jobs.router)
app.include_router(cmdb.router)
app.include_router(playbooks.router)