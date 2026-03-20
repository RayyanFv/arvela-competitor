from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict

import yaml


class Notifier:
    def __init__(self, root: Path | None = None, company_id: str | None = None, webhook_url: str | None = None):
        self.root = root
        self.company_id = company_id
        self.webhook_url = webhook_url or self._resolve_webhook_url()

    def notify(self, event_type: str, payload: Dict[str, Any]) -> bool:
        if not self.is_enabled_for_event(event_type):
            return False
        if not self.webhook_url:
            return False
        body = {"event_type": event_type, "payload": payload}
        req = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15):
                return True
        except Exception:
            return False

    def is_enabled_for_event(self, event_type: str) -> bool:
        cfg = self._load_cfg()
        events = cfg.get("events", {})
        if event_type in events:
            return bool(events[event_type])
        return bool(cfg.get("enabled", False))

    def _resolve_webhook_url(self) -> str:
        cfg = self._load_cfg()
        return str(cfg.get("webhook_url") or os.getenv("BOARD_WEBHOOK_URL", ""))

    def _load_cfg(self) -> Dict[str, Any]:
        if not self.root or not self.company_id:
            return {"enabled": True, "events": {}}
        p = self.root / "config" / "notifications" / f"{self.company_id}.yaml"
        if not p.exists():
            return {"enabled": True, "events": {}}
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {"enabled": True, "events": {}}
