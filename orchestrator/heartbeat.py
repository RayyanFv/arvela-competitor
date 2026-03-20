from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


class HeartbeatScheduler:
    def __init__(self, root: Path, company_id: str):
        self.root = root
        self.company_id = company_id
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.path = root / "storage" / company_id / "audit" / "heartbeat.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._started = False

    def start(
        self,
        agents_cfg: List[Dict[str, Any]],
        on_fire: Callable[[str], None] | None = None,
        interval_seconds: int | None = None,
        agent_ids: List[str] | None = None,
    ) -> None:
        if self._started:
            return
        allowed = set(agent_ids or [])
        for cfg in agents_cfg:
            agent_id = cfg.get("agent_id", "unknown")
            if allowed and agent_id not in allowed:
                continue
            hb = cfg.get("heartbeat", {})
            if not hb.get("enabled", False):
                continue
            trigger = None
            if interval_seconds and interval_seconds > 0:
                trigger = IntervalTrigger(seconds=interval_seconds)
            else:
                cron = hb.get("schedule", "")
                if not cron:
                    continue
                trigger = CronTrigger.from_crontab(cron)
            self.scheduler.add_job(
                self._fire,
                trigger=trigger,
                id=f"hb_{agent_id}",
                replace_existing=True,
                kwargs={"agent_id": agent_id, "on_fire": on_fire},
            )
        self.scheduler.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self.scheduler.shutdown(wait=False)
        self._started = False

    def status(self) -> Dict[str, Any]:
        jobs = []
        for j in self.scheduler.get_jobs():
            jobs.append({"id": j.id, "next_run": str(j.next_run_time)})
        return {"running": self._started, "jobs": jobs}

    def list_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out = [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
        return out[-max(1, int(limit)) :]

    def record_event(self, event: str, data: Dict[str, Any]) -> Dict[str, Any]:
        item = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), "data": data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=True) + "\n")
        return item

    def _fire(self, agent_id: str, on_fire: Callable[[str], None] | None = None) -> None:
        self.record_event("heartbeat_fired", {"agent_id": agent_id})
        if on_fire:
            on_fire(agent_id)
