from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

from orchestrator.engine import PipelineEngine
from orchestrator.event_bus import EventBus
from orchestrator.heartbeat import HeartbeatScheduler
from orchestrator.notifier import Notifier
from orchestrator.override import OverrideManager
from orchestrator.ticket_system import TicketSystem

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="Arvela Mobile API", version="1.0.0")
HEARTBEAT_MANAGERS: Dict[str, HeartbeatScheduler] = {}


class PipelineRunRequest(BaseModel):
    objective: str


class BoardOverrideRequest(BaseModel):
    action: str
    payload: Dict[str, Any]


class NotificationRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    webhook_url: str | None = None


class CompanyCreateRequest(BaseModel):
    company_id: str
    display_name: str
    industry: str = "SaaS"
    stage: str = "early_growth"
    target_market: str = "SMB"
    mission: str = "Build measurable value"


class NotificationConfigRequest(BaseModel):
    enabled: bool = True
    webhook_url: str = ""
    events: Dict[str, bool] = {}


class HeartbeatStartRequest(BaseModel):
    interval_seconds: int | None = None
    agent_roles: list[str] | None = None


def _load_company(company_id: str) -> Dict[str, Any]:
    company_path = ROOT / "config" / "companies" / f"{company_id}.yaml"
    if company_path.exists():
        return yaml.safe_load(company_path.read_text(encoding="utf-8"))
    path = ROOT / "config" / "company.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="company config not found")
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if obj.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="company not found")
    return obj


def _load_heartbeat_routes() -> Dict[str, Any]:
    p = ROOT / "config" / "heartbeat_routes.yaml"
    if not p.exists():
        return {"routes": {}}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {"routes": {}}


def _notif_cfg_path(company_id: str) -> Path:
    return ROOT / "config" / "notifications" / f"{company_id}.yaml"


@app.get("/api/v1/{company_id}/agents")
def list_agents(company_id: str):
    _load_company(company_id)
    out = []
    for aid in ["ceo", "cpo", "cto", "cmo"]:
        p = ROOT / "config" / "agents" / f"{aid}.yaml"
        if not p.exists():
            continue
        cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
        out.append({"agent_id": aid, "display_name": cfg.get("display_name"), "enabled": cfg.get("enabled", True)})
    return {"items": out}


@app.get("/api/v1/{company_id}/agents/{agent_id}")
def get_agent(company_id: str, agent_id: str):
    _load_company(company_id)
    p = ROOT / "config" / "agents" / f"{agent_id}.yaml"
    if not p.exists():
        raise HTTPException(status_code=404, detail="agent not found")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    return cfg


@app.post("/api/v1/{company_id}/agents/{agent_id}/pause")
def pause_agent(company_id: str, agent_id: str):
    _load_company(company_id)
    ov = OverrideManager(ROOT, company_id)
    return ov.pause_agent(agent_id)


@app.post("/api/v1/{company_id}/agents/{agent_id}/resume")
def resume_agent(company_id: str, agent_id: str):
    _load_company(company_id)
    ov = OverrideManager(ROOT, company_id)
    return ov.resume_agent(agent_id)


@app.get("/api/v1/{company_id}/budgets")
def get_budgets(company_id: str):
    _load_company(company_id)
    p = ROOT / "storage" / "budgets" / f"{company_id}.json"
    if not p.exists():
        return {"message": "budget ledger not initialized"}
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/v1/{company_id}/pipelines")
def list_pipelines(company_id: str):
    _load_company(company_id)
    out = []
    for p in (ROOT / "config" / "pipelines").glob("*.yaml"):
        cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
        if cfg.get("company_id") == company_id:
            out.append({"pipeline_id": cfg.get("pipeline_id"), "enabled": cfg.get("enabled", True)})
    return {"items": out}


@app.post("/api/v1/{company_id}/pipelines/{pipeline_id}/run")
def run_pipeline(company_id: str, pipeline_id: str, req: PipelineRunRequest):
    _load_company(company_id)
    engine = PipelineEngine(ROOT)
    result = engine.run(pipeline_id, req.objective, company_id=company_id)
    return result


@app.get("/api/v1/{company_id}/tickets")
def list_tickets(company_id: str):
    _load_company(company_id)
    ts = TicketSystem(ROOT, company_id)
    return {"items": ts.list_tickets()}


@app.get("/api/v1/{company_id}/tickets/{ticket_id}")
def get_ticket(company_id: str, ticket_id: str):
    _load_company(company_id)
    ts = TicketSystem(ROOT, company_id)
    for t in ts.list_tickets():
        if t["ticket_id"] == ticket_id:
            return t
    raise HTTPException(status_code=404, detail="ticket not found")


@app.post("/api/v1/{company_id}/board/override")
def board_override(company_id: str, req: BoardOverrideRequest):
    _load_company(company_id)
    ov = OverrideManager(ROOT, company_id)
    return ov.log(req.action, req.payload)


@app.get("/api/v1/{company_id}/runs")
def list_runs(company_id: str):
    _load_company(company_id)
    base = ROOT / "storage" / company_id / "outputs"
    if not base.exists():
        return {"items": []}
    runs = [p.name for p in base.iterdir() if p.is_dir() and p.name.startswith("run_")]
    runs.sort(reverse=True)
    return {"items": runs}


@app.get("/api/v1/{company_id}/runs/{run_id}/report")
def get_run_report(company_id: str, run_id: str):
    _load_company(company_id)
    p = ROOT / "storage" / company_id / "outputs" / run_id / "combined_report.md"
    if not p.exists():
        raise HTTPException(status_code=404, detail="combined report not found")
    return {"run_id": run_id, "combined_report": p.read_text(encoding="utf-8")}


@app.post("/api/v1/{company_id}/heartbeat/start")
def heartbeat_start(company_id: str, req: HeartbeatStartRequest | None = None):
    _load_company(company_id)
    manager = HEARTBEAT_MANAGERS.get(company_id)
    if manager is None:
        manager = HeartbeatScheduler(ROOT, company_id)
        HEARTBEAT_MANAGERS[company_id] = manager

    agents = []
    for p in (ROOT / "config" / "agents").glob("*.yaml"):
        cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
        if cfg.get("company_id") == company_id:
            agents.append(cfg)

    def _on_fire(agent_id: str) -> None:
        routes = _load_heartbeat_routes().get("routes", {})
        route = routes.get(agent_id, {})
        pipeline_id = route.get("pipeline_id", "full_run")
        tpl = route.get("objective_template", "Heartbeat trigger for {agent_id} ({company_id})")
        objective = tpl.format(agent_id=agent_id, company_id=company_id)
        engine = PipelineEngine(ROOT)
        try:
            engine.run(pipeline_id, objective, company_id=company_id)
        except Exception:
            pass

    interval_seconds = req.interval_seconds if req else None
    agent_roles = req.agent_roles if req else None
    manager.start(agents, on_fire=_on_fire, interval_seconds=interval_seconds, agent_ids=agent_roles)
    return manager.status()


@app.post("/api/v1/{company_id}/heartbeat/stop")
def heartbeat_stop(company_id: str):
    _load_company(company_id)
    manager = HEARTBEAT_MANAGERS.get(company_id)
    if manager is None:
        return {"running": False, "jobs": []}
    manager.stop()
    return manager.status()


@app.get("/api/v1/{company_id}/heartbeat/status")
def heartbeat_status(company_id: str):
    _load_company(company_id)
    manager = HEARTBEAT_MANAGERS.get(company_id)
    if manager is None:
        return {"running": False, "jobs": []}
    return manager.status()


@app.get("/api/v1/{company_id}/heartbeat/events")
def heartbeat_events(company_id: str):
    _load_company(company_id)
    manager = HEARTBEAT_MANAGERS.get(company_id)
    if manager is None:
        return {"items": []}
    return {"items": manager.list_events(200)}


@app.post("/api/v1/{company_id}/notifications/test")
def notification_test(company_id: str, req: NotificationRequest):
    _load_company(company_id)
    notifier = Notifier(ROOT, company_id, webhook_url=req.webhook_url)
    ok = notifier.notify(req.event_type, req.payload)
    return {"sent": ok, "event_type": req.event_type}


@app.get("/api/v1/{company_id}/events")
def list_events(company_id: str):
    _load_company(company_id)
    eb = EventBus(ROOT, company_id)
    return {"items": eb.list_events(200)}


@app.get("/api/v1/companies")
def list_companies():
    out = []
    base = ROOT / "config" / "companies"
    if base.exists():
        for p in sorted(base.glob("*.yaml")):
            obj = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            out.append(
                {
                    "company_id": obj.get("company_id", p.stem),
                    "display_name": obj.get("display_name", p.stem),
                    "industry": obj.get("industry", ""),
                    "stage": obj.get("stage", ""),
                }
            )

    default_path = ROOT / "config" / "company.yaml"
    if default_path.exists():
        obj = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}
        cid = obj.get("company_id")
        if cid and not any(x["company_id"] == cid for x in out):
            out.append(
                {
                    "company_id": cid,
                    "display_name": obj.get("display_name", cid),
                    "industry": obj.get("industry", ""),
                    "stage": obj.get("stage", ""),
                }
            )
    return {"items": out}


@app.post("/api/v1/companies")
def create_company(req: CompanyCreateRequest):
    out = ROOT / "config" / "companies" / f"{req.company_id}.yaml"
    if out.exists():
        raise HTTPException(status_code=409, detail="company already exists")
    payload = {
        "company_id": req.company_id,
        "display_name": req.display_name,
        "industry": req.industry,
        "stage": req.stage,
        "target_market": req.target_market,
        "mission": req.mission,
        "okrs": [],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    for d in [
        ROOT / "storage" / req.company_id / "outputs",
        ROOT / "storage" / req.company_id / "audit",
        ROOT / "storage" / req.company_id / "memory",
    ]:
        d.mkdir(parents=True, exist_ok=True)
    return {"created": True, "company_id": req.company_id}


@app.get("/api/v1/{company_id}/notifications/config")
def get_notification_config(company_id: str):
    _load_company(company_id)
    p = _notif_cfg_path(company_id)
    if not p.exists():
        return {"enabled": True, "webhook_url": "", "events": {}}
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@app.post("/api/v1/{company_id}/notifications/config")
def set_notification_config(company_id: str, req: NotificationConfigRequest):
    _load_company(company_id)
    p = _notif_cfg_path(company_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"enabled": req.enabled, "webhook_url": req.webhook_url, "events": req.events}
    p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return {"saved": True}
