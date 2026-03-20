from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class MemoryStore:
    def __init__(self, root: Path, company_id: str):
        self.base = root / "storage" / company_id / "memory"
        self.base.mkdir(parents=True, exist_ok=True)

    def append(self, agent_id: str, output_key: str, content: str, max_entries: int = 20) -> None:
        path = self.base / f"{agent_id}.jsonl"
        rows = self._read(path)
        rows.append(
            {
                "agent_id": agent_id,
                "output_key": output_key,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        rows = rows[-max(1, int(max_entries)) :]
        path.write_text("\n".join(json.dumps(r, ensure_ascii=True) for r in rows), encoding="utf-8")

    def latest(self, agent_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        path = self.base / f"{agent_id}.jsonl"
        rows = self._read(path)
        return rows[-max(1, int(limit)) :]

    def latest_text(self, agent_id: str, limit: int = 3, max_words_each: int = 120) -> str:
        chunks = []
        for row in self.latest(agent_id, limit):
            words = str(row.get("content", "")).split()
            snippet = " ".join(words[:max_words_each])
            chunks.append(snippet)
        return "\n\n".join(chunks)

    def _read(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        out: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out
