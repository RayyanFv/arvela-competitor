from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class EventBus:
    def __init__(self, root: Path, company_id: str):
        self.path = root / "storage" / company_id / "audit" / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event_type: str, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "event_type": event_type,
            "source": source,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")
        return event

    def list_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        out = [json.loads(x) for x in lines if x.strip()]
        return out[-max(1, int(limit)) :]
