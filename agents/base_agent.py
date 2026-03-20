from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


@dataclass
class AgentResult:
    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    used_model: str
    provider_trace: List[Dict[str, str]]


class BaseAgent:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_id = config["agent_id"]
        self.title = config["role"]["title"]
        self.system_prompt = config["system_prompt"]
        self.model = config["model"]["primary"]
        self.fallback = config["model"]["fallback"]
        self.temperature = float(config["model"].get("temperature", 0.3))
        self.max_tokens = int(config["model"].get("max_tokens", 1200))
        self.timeout_seconds = int(config["model"].get("timeout_seconds", 120))

    def run(self, task: str, context: Dict[str, Any], retry_suffix: str = "") -> AgentResult:
        prompt = self._build_prompt(task, context, retry_suffix)
        trace: List[Dict[str, str]] = []
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if api_key:
            content, used = "", ""
            ok = False
            for model in self._candidate_models():
                ok, content, used, err = self._call_openrouter(prompt, model)
                trace.append({"model": model, "status": "ok" if ok else "error", "error": err})
                if ok:
                    break
            if not ok:
                content, used = self._mock_response(task, context), "mock:provider_unavailable"
        else:
            content, used = self._mock_response(task, context), "mock:no_api_key"
            trace.append({"model": "none", "status": "error", "error": "missing OPENROUTER_API_KEY"})

        in_tokens = max(1, len(prompt.split()))
        out_tokens = max(1, len(content.split()))
        # Cheap approximation for free/open models while keeping ledger shape.
        cost_usd = round((in_tokens + out_tokens) / 1_000_000, 6)
        return AgentResult(content, in_tokens, out_tokens, cost_usd, used, trace)

    def _build_prompt(self, task: str, context: Dict[str, Any], retry_suffix: str) -> str:
        ctx = "\n".join(f"{k}: {v}" for k, v in context.items())
        required = self._required_markers_hint()
        return (
            f"SYSTEM:\n{self.system_prompt}\n\n"
            f"CONTEXT:\n{ctx}\n\n"
            f"TASK:\n{task}\n\n"
            "MANDATORY OUTPUT RULES:\n"
            "- Follow the exact section headers from SYSTEM output format.\n"
            "- Start directly with the first required markdown header (## ...).\n"
            "- Do not omit required sections.\n\n"
            f"DoD markers to satisfy:\n{required}\n\n"
            f"{retry_suffix}".strip()
        )

    def _required_markers_hint(self) -> str:
        items: List[str] = []
        for rule in self.config.get("definition_of_done", []):
            check = rule.get("check")
            val = rule.get("value")
            if check in {"present", "contains_keyword"}:
                if isinstance(val, list):
                    items.extend(str(v) for v in val)
                elif val is not None:
                    items.append(str(val))
        if not items:
            return "- Include all required output sections"
        uniq = []
        for i in items:
            if i not in uniq:
                uniq.append(i)
        return "\n".join(f"- {u}" for u in uniq[:20])

    def _candidate_models(self) -> List[str]:
        models: List[str] = []
        # Prefer paid/non-free variants first when API key is available.
        for m in [self.model, self.fallback]:
            if isinstance(m, str) and m.endswith(":free"):
                models.append(m[:-5])
            models.append(m)
        dedup: List[str] = []
        for m in models:
            if m and m not in dedup:
                dedup.append(m)
        return dedup

    def _call_openrouter(self, prompt: str, model: str) -> Tuple[bool, str, str, str]:
        try:
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "arvela-ai-os",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            msg = payload["choices"][0]["message"]["content"]
            if isinstance(msg, list):
                text = "\n".join(part.get("text", "") for part in msg if isinstance(part, dict))
            else:
                text = str(msg)
            return True, text, model, ""
        except Exception as e:
            # Small backoff helps with bursty provider 429s.
            time.sleep(0.8)
            return False, "", model, str(e)

    def _mock_response(self, task: str, context: Dict[str, Any]) -> str:
        objective = context.get("objective", "Ship measurable progress")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        role = self.title.lower()
        if "executive" in role or "ceo" in role:
            return (
                "## Strategic Summary\n"
                f"Date: {now}. Objective focus: {objective}.\n"
                "We align product, engineering, and GTM on one sprint target with explicit ownership.\n\n"
                "## Decision\n"
                "Go: proceed with the scoped sprint plan and review risk mid-sprint.\n\n"
                "## Top 3 Priorities (this sprint)\n"
                "1. Scope top features - cpo - 2 validated stories\n"
                "2. Ship API + QA baseline - cto - all checks green\n"
                "3. Run ICP campaign - cmo - 20 SQLs\n\n"
                "## Risks\n"
                "- Delivery slippage: reduce scope and enforce daily check-in\n\n"
                "## OKR Status\n"
                "PMF OKR trend: improving, grade B\n\n"
                "## Open Questions\n"
                "What integration should be first for Indonesian SMEs?\n"
            )
        if "product" in role or "cpo" in role:
            return (
                "## Market Insight\n"
                "SMEs want speed to value, simple onboarding, and clear ROI before adopting HR tools.\n\n"
                "## Feature Prioritization\n"
                "| Feature | R | I | C | E | RICE | Sprint |\n"
                "|---|---|---|---|---|---|---|\n"
                "| Hiring funnel dashboard | 8 | 7 | 7 | 4 | 98 | 1 |\n"
                "| Candidate scoring rubric | 6 | 8 | 6 | 5 | 57.6 | 1 |\n"
                "| Payroll sync export | 5 | 7 | 6 | 6 | 35 | 2 |\n\n"
                "## Top Priority: User Stories\n"
                "### Story 1: Faster screening\n"
                "As an HR manager, I want ranked candidates so that I shortlist faster.\n"
                "**Acceptance Criteria:**\n- [ ] rank visible\n- [ ] filter by role\n- [ ] export shortlist\n\n"
                "### Story 2: Better hiring visibility\n"
                "As a founder, I want funnel metrics so that I spot bottlenecks.\n"
                "**Acceptance Criteria:**\n- [ ] stage conversion\n- [ ] time to hire\n- [ ] source quality\n\n"
                "## Open Questions for CTO\n1. Can ranking run async within 2 seconds SLA?\n\n"
                "## Metrics to Watch\n- Activation rate: current=22, target=35\n"
            )
        if "technology" in role or "cto" in role:
            return (
                "## Architecture Decision\n"
                "- Context: Need fast delivery for sprint scope.\n"
                "- Options considered: monolith API vs split services.\n"
                "- Decision: monolith API with modular domains.\n"
                "- Consequences: faster shipping, limited scaling flexibility.\n\n"
                "## Implementation Tasks\n"
                "| # | Task | File/Component | Est. Hours | Depends On |\n"
                "|---|---|---|---|---|\n"
                "| 1 | Candidate ranking endpoint | app/api/ranking | 6 | schema |\n"
                "| 2 | Funnel metrics query | app/api/funnel | 4 | events |\n"
                "| 3 | QA regression suite | tests/hiring | 5 | tasks 1-2 |\n\n"
                "## Tech Debt Register (this sprint)\n"
                "| ID | Description | Severity | Impact if ignored |\n"
                "|---|---|---|---|\n"
                "| TD-1 | Missing typed API responses | P1 | runtime bugs |\n\n"
                "## QA Checklist\n"
                "### Hiring Flow\n"
                "- [ ] Unit: ranking score calc\n- [ ] Integration: API + DB\n- [ ] E2E: shortlist flow\n- [ ] Manual: mobile viewport\n- [ ] Security: role access\n\n"
                "## Security & Compliance\n"
                "- PDP flag: yes, employee data encryption at rest required\n"
                "- Auth concern: enforce RBAC on metrics endpoint\n"
                "- Data sensitivity: personal identifiable data\n\n"
                "## CPO Questions - Answered\n"
                "1. Q: Can ranking run async within 2 seconds SLA? -> A: yes with queue + cache.\n"
            )
        return (
            "## ICP Card\n"
            "Industry vertical: HR SaaS\nHeadcount range: 50-500\nHR maturity level: basic\n"
            "Decision maker title: HR Manager\nBudget range (IDR): 5-20M/month\n"
            "Top 3 pains: slow hiring, scattered data, weak reporting\nDeal velocity (avg days to close): 30\n\n"
            "## Positioning Statement\n"
            "For Indonesian SMEs needing faster hiring, Arvela is an HR operating platform that unifies posting, assessment, and operations; unlike fragmented tools, we provide measurable funnel visibility from day one.\n\n"
            "## GTM Channel Plan\n"
            "| Channel | Audience | Message | Format | Frequency | KPI |\n"
            "|---|---|---|---|---|---|\n"
            "| LinkedIn outbound | HR leads | reduce time-to-hire | DM + case | weekly | replies |\n"
            "| Webinar | founders | hiring ROI | live demo | biweekly | attendees |\n"
            "| Partner referrals | HR communities | simplify HR ops | co-marketing | monthly | SQL |\n\n"
            "## Sales Playbook\n"
            "### Outreach Cadence (5 steps)\n"
            "Day 1 / Day 3 / Day 7 / Day 14 / Day 21: connect, value proof, demo invite, objection handling, close ask\n\n"
            "### Qualification (BANT-ID)\n"
            "- Budget / Authority / Need / Timeline / Existing HRIS?\n\n"
            "### Top 3 Objections\n"
            "1. \"Mahal\" -> \"Kami mulai dari paket bertahap sesuai jumlah karyawan.\"\n"
            "2. \"Implementasi lama\" -> \"Onboarding standar selesai dalam 7-10 hari.\"\n"
            "3. \"Data aman?\" -> \"Data dienkripsi dan akses berbasis peran.\"\n\n"
            "## Business Development\n"
            "| Partner Type | Named Target | Value Exchange | Next Action |\n"
            "|---|---|---|---|\n"
            "| HR community | Glints Community | leads + content | intro email |\n"
            "| Payroll | Mekari partner | integration reach | discovery call |\n"
            "| Recruiter network | Kalibrr ecosystem | referrals | pilot proposal |\n\n"
            "## Account Management Playbook\n"
            "- Churn signal 1: low weekly login -> action: CSM check-in\n"
            "- Churn signal 2: no jobs posted 30 days -> action: reactivation offer\n"
            "- Upsell trigger: hiring volume up -> pitch: assessment module\n\n"
            "## 90-Day Metrics\n"
            "| Metric | Current | Target | Owner |\n"
            "|---|---|---|---|\n"
            "| MQL | 40 | 120 | CMO |\n"
            "| SQL | 15 | 50 | CMO |\n"
            "| Win rate | 12 | 20 | CMO |\n"
            "| CAC | 320 | 250 | CMO |\n"
            "| LTV/CAC | 2.0 | 3.0 | CMO |\n"
        )
