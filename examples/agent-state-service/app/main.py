import os
import socket
import threading
import time
from datetime import datetime, timezone
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="agent-state-service")

SERVICE = "agent-state-service"
VERSION = os.getenv("APP_VERSION", "1.0.0")


class AgentStatus(str, Enum):
    up = "up"
    down = "down"
    unknown = "unknown"


class Agent(BaseModel):
    tenant: str
    agent_id: str
    status: AgentStatus = AgentStatus.unknown
    last_seen: str | None = None


class StatusUpdate(BaseModel):
    status: AgentStatus


# In-memory store keyed by (tenant, agent_id).
# NOTE: per-pod and ephemeral. When scaled to many replicas this is NOT shared.
# Production must back this with a shared store (Redis / Postgres) — see plan doc.
_store: dict[tuple[str, str], Agent] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/")
def root():
    return {"service": SERVICE, "pod": socket.gethostname(), "version": VERSION}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.get("/stats")
def stats():
    with _lock:
        agents = list(_store.values())
    counts: dict[str, int] = {s.value: 0 for s in AgentStatus}
    tenants: set[str] = set()
    for a in agents:
        counts[a.status.value] += 1
        tenants.add(a.tenant)
    return {
        "pod": socket.gethostname(),
        "tenants": len(tenants),
        "agents": len(agents),
        "by_status": counts,
    }


@app.get("/tenants/{tenant}/agents")
def list_agents(tenant: str):
    with _lock:
        agents = [a for a in _store.values() if a.tenant == tenant]
    return {"tenant": tenant, "count": len(agents), "agents": agents}


@app.get("/tenants/{tenant}/agents/{agent_id}")
def get_agent(tenant: str, agent_id: str):
    with _lock:
        agent = _store.get((tenant, agent_id))
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return agent


@app.put("/tenants/{tenant}/agents/{agent_id}")
def upsert_agent(tenant: str, agent_id: str, body: StatusUpdate):
    agent = Agent(
        tenant=tenant, agent_id=agent_id, status=body.status, last_seen=_now()
    )
    with _lock:
        _store[(tenant, agent_id)] = agent
    return agent


def _set_status(tenant: str, agent_id: str, status: AgentStatus) -> Agent:
    with _lock:
        agent = _store.get((tenant, agent_id)) or Agent(
            tenant=tenant, agent_id=agent_id
        )
        agent.status = status
        agent.last_seen = _now()
        _store[(tenant, agent_id)] = agent
    return agent


@app.post("/tenants/{tenant}/agents/{agent_id}/up")
def mark_up(tenant: str, agent_id: str):
    return _set_status(tenant, agent_id, AgentStatus.up)


@app.post("/tenants/{tenant}/agents/{agent_id}/down")
def mark_down(tenant: str, agent_id: str):
    return _set_status(tenant, agent_id, AgentStatus.down)


@app.post("/tenants/{tenant}/agents/{agent_id}/heartbeat")
def heartbeat(tenant: str, agent_id: str):
    return _set_status(tenant, agent_id, AgentStatus.up)


@app.delete("/tenants/{tenant}/agents/{agent_id}", status_code=204)
def delete_agent(tenant: str, agent_id: str):
    with _lock:
        _store.pop((tenant, agent_id), None)
    return None


@app.get("/load")
def load(ms: int = 200):
    # Synthetic CPU load to validate HorizontalPodAutoscaler behavior.
    ms = max(0, min(ms, 5000))
    deadline = time.monotonic() + (ms / 1000.0)
    iterations = 0
    while time.monotonic() < deadline:
        iterations += 1
        _ = sum(i * i for i in range(1000))
    return {"burned_ms": ms, "iterations": iterations, "pod": socket.gethostname()}
