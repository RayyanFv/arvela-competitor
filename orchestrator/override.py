from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class OverrideManager:
    def __init__(self, root: Path, company_id: str):
        self.base = root / "storage" / company_id / "audit"
        self.base.mkdir(parents=True, exist_ok=True)
        self.events = self.base / "board_overrides.jsonl"

    def log(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "event": "BOARD_OVERRIDE",
            "action": action,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self.events.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")
        return event

    def pause_agent(self, agent_id: str) -> Dict[str, Any]:
        return self.log("pause_agent", {"agent_id": agent_id})

    def resume_agent(self, agent_id: str) -> Dict[str, Any]:
        return self.log("resume_agent", {"agent_id": agent_id})

    def terminate_run(self, run_id: str) -> Dict[str, Any]:
        return self.log("terminate_run", {"run_id": run_id})

    def override_dod(self, ticket_id: str) -> Dict[str, Any]:
        return self.log("override_dod", {"ticket_id": ticket_id})

    def inject_context(self, key: str, val: Any) -> Dict[str, Any]:
        return self.log("inject_context", {"key": key, "val": val})

    def reset_budget(self, agent_id: str) -> Dict[str, Any]:
        return self.log("reset_budget", {"agent_id": agent_id})
