from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class TicketSystem:
    def __init__(self, root: Path, company_id: str):
        self.path = root / "storage" / company_id / "audit" / "tickets.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def create_ticket(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        ticket = {
            "ticket_id": f"TKT-{now.strftime('%Y%m%d-%H%M%S')}-{payload['agent_id']}",
            "run_id": payload["run_id"],
            "pipeline_id": payload["pipeline_id"],
            "company_id": payload["company_id"],
            "agent_id": payload["agent_id"],
            "status": payload.get("status", "complete"),
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": int(payload.get("duration_seconds", 0)),
            "input": payload.get("input", {}),
            "output": payload.get("output", {}),
            "model": payload.get("model", {}),
            "dod": payload.get("dod", {}),
            "audit_hash": payload.get("audit_hash", "sha256:na"),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ticket, ensure_ascii=True) + "\n")
        return ticket

    def list_tickets(self, run_id: str | None = None) -> list[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if run_id and obj.get("run_id") != run_id:
                continue
            out.append(obj)
        return out
