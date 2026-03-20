from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


@dataclass
class BudgetStatus:
    allowed: bool
    reason: str


class BudgetLedger:
    def __init__(self, root: Path, company_id: str):
        self.root = root
        self.company_id = company_id
        self.path = root / "storage" / "budgets" / f"{company_id}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_or_init(self, company_limits: Dict[str, float]) -> Dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))

        month = datetime.now(timezone.utc).strftime("%Y-%m")
        total = sum(company_limits.values())
        ledger = {
            "company_id": self.company_id,
            "period": month,
            "agents": {
                k: {
                    "monthly_limit_usd": v,
                    "consumed_usd": 0.0,
                    "consumed_pct": 0.0,
                    "runs_this_month": 0,
                    "avg_cost_per_run": 0.0,
                    "token_breakdown": {"input_tokens": 0, "output_tokens": 0},
                    "status": "active",
                }
                for k, v in company_limits.items()
            },
            "pipeline_costs": [],
            "totals": {
                "monthly_limit_usd": total,
                "consumed_usd": 0.0,
                "consumed_pct": 0.0,
                "projected_month_end_usd": 0.0,
            },
        }
        self.save(ledger)
        return ledger

    def save(self, ledger: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    def check_agent_can_run(self, ledger: Dict[str, Any], agent_id: str) -> BudgetStatus:
        a = ledger["agents"].get(agent_id)
        if not a:
            return BudgetStatus(False, f"missing budget config for {agent_id}")
        if a["consumed_usd"] >= a["monthly_limit_usd"]:
            a["status"] = "over-budget"
            self.save(ledger)
            return BudgetStatus(False, f"agent {agent_id} monthly limit reached")
        return BudgetStatus(True, "ok")

    def check_pipeline_can_run(self, ledger: Dict[str, Any], pipeline_max_total_usd: float, run_spent: float) -> BudgetStatus:
        if run_spent >= pipeline_max_total_usd:
            return BudgetStatus(False, "pipeline budget exceeded")
        return BudgetStatus(True, "ok")

    def register_agent_cost(
        self,
        ledger: Dict[str, Any],
        agent_id: str,
        cost_usd: float,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        a = ledger["agents"][agent_id]
        a["consumed_usd"] = round(a["consumed_usd"] + cost_usd, 6)
        a["runs_this_month"] += 1
        a["avg_cost_per_run"] = round(a["consumed_usd"] / max(1, a["runs_this_month"]), 6)
        a["consumed_pct"] = round((a["consumed_usd"] / a["monthly_limit_usd"]) * 100, 2) if a["monthly_limit_usd"] else 0
        a["token_breakdown"]["input_tokens"] += int(input_tokens)
        a["token_breakdown"]["output_tokens"] += int(output_tokens)
        if a["consumed_usd"] >= a["monthly_limit_usd"]:
            a["status"] = "over-budget"

    def register_pipeline_cost(self, ledger: Dict[str, Any], run_id: str, pipeline_id: str, per_agent: Dict[str, float]) -> None:
        total = round(sum(per_agent.values()), 6)
        ledger["pipeline_costs"].append(
            {
                "run_id": run_id,
                "pipeline_id": pipeline_id,
                "total_cost_usd": total,
                "agents": per_agent,
            }
        )
        t = ledger["totals"]
        t["consumed_usd"] = round(sum(a["consumed_usd"] for a in ledger["agents"].values()), 6)
        t["consumed_pct"] = round((t["consumed_usd"] / t["monthly_limit_usd"]) * 100, 2) if t["monthly_limit_usd"] else 0
        t["projected_month_end_usd"] = t["consumed_usd"]
