from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import yaml

from agents import AGENT_CLASS_MAP
from orchestrator.budget_ledger import BudgetLedger
from orchestrator.context_bus import build_agent_input, build_start_context
from orchestrator.dod_validator import DoDValidator
from orchestrator.event_bus import EventBus
from orchestrator.heartbeat import HeartbeatScheduler
from orchestrator.memory_store import MemoryStore
from orchestrator.notifier import Notifier
from orchestrator.ticket_system import TicketSystem


class PipelineEngine:
    def __init__(self, root: Path):
        self.root = root
        self.validator = DoDValidator()
    def run(self, pipeline_id: str, objective: str, company_id: str | None = None) -> Dict[str, Any]:
        if not objective.strip():
            raise ValueError("objective is required")

        company = self._load_company(company_id)
        pipeline = self._load_yaml(self.root / "config" / "pipelines" / f"{pipeline_id}.yaml")
        if not pipeline.get("enabled", True):
            raise RuntimeError(f"pipeline {pipeline_id} is disabled")

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        company_context = self._company_summary(company)
        context = build_start_context(company["company_id"], objective, company_context, run_id)
        context["pipeline_id"] = pipeline_id
        context["_run_spent_usd"] = 0.0

        active_company_id = company["company_id"]
        events = EventBus(self.root, active_company_id)
        self.heartbeat = HeartbeatScheduler(self.root, active_company_id)
        notifier = Notifier(self.root, active_company_id)
        monthly_limits = self._agent_monthly_limits(active_company_id)
        ledger = BudgetLedger(self.root, active_company_id)
        ledger_data = ledger.load_or_init(monthly_limits)
        ticketing = TicketSystem(self.root, active_company_id)
        memory = MemoryStore(self.root, active_company_id)

        events.emit("new_objective", "orchestrator", {"run_id": run_id, "objective": objective})

        for step in sorted(pipeline["sequence"], key=lambda x: x["step"]):
            self._run_step(step, pipeline, context, ledger, ledger_data, ticketing, memory, events, notifier)

        ledger.register_pipeline_cost(ledger_data, run_id, pipeline_id, context["_costs"])
        ledger.save(ledger_data)
        hb_evt = self.heartbeat.record_event("pipeline_complete", {"company_id": active_company_id, "run_id": run_id})
        events.emit("pipeline_complete", "orchestrator", hb_evt)
        notifier.notify("pipeline_complete", {"company_id": active_company_id, "run_id": run_id})

        combined = self._save_combined_report(context)
        return {"run_id": run_id, "combined_report": str(combined)}

    def _run_step(
        self,
        step: Dict[str, Any],
        pipeline: Dict[str, Any],
        context: Dict[str, Any],
        ledger: BudgetLedger,
        ledger_data: Dict[str, Any],
        ticketing: TicketSystem,
        memory: MemoryStore,
        events: EventBus,
        notifier: Notifier,
    ) -> None:
        agent_id = step["agent_id"]
        cfg = self._load_yaml(self.root / "config" / "agents" / f"{agent_id}.yaml")
        if not cfg.get("enabled", True):
            return

        allow = ledger.check_agent_can_run(ledger_data, agent_id)
        if not allow.allowed:
            events.emit("budget_limit_hit", "budget_ledger", {"agent_id": agent_id, "reason": allow.reason})
            notifier.notify("budget_limit_hit", {"agent_id": agent_id, "reason": allow.reason})
            raise RuntimeError(allow.reason)

        max_total = float(pipeline.get("pipeline_budget", {}).get("max_total_usd", 999999))
        pcheck = ledger.check_pipeline_can_run(ledger_data, max_total, float(context.get("_run_spent_usd", 0.0)))
        if not pcheck.allowed:
            action = pipeline.get("pipeline_budget", {}).get("on_exceeded", "halt")
            if action in {"halt", "skip_remaining"}:
                events.emit("pipeline_budget_exceeded", "budget_ledger", {"run_id": context.get("run_id")})
                notifier.notify("pipeline_budget_exceeded", {"run_id": context.get("run_id")})
                raise RuntimeError(pcheck.reason)
            return

        klass = AGENT_CLASS_MAP.get(agent_id)
        if not klass:
            raise RuntimeError(f"unknown agent_id: {agent_id}")

        task = step["task"]
        inputs = build_agent_input(context, cfg.get("input_context_keys", []))
        mem_cfg = cfg.get("memory", {})
        if mem_cfg.get("enabled", False):
            inputs["prior_memory"] = memory.latest_text(agent_id, limit=3, max_words_each=120)
        agent = klass(cfg)

        retries = int(pipeline.get("on_dod_failure", {}).get("max_retries", 1))
        retry_suffix = ""
        final = None
        failed_checks = []
        started = time.time()

        for _ in range(retries + 1):
            result = agent.run(task=task, context=inputs, retry_suffix=retry_suffix)
            ok, failed_checks = self.validator.validate(result.content, cfg.get("definition_of_done", []))
            final = result
            if ok:
                break
            retry_suffix = (
                "Your previous output failed these checks: "
                f"{', '.join(failed_checks)}. Fix them and keep the same format."
            )

        if final is None:
            raise RuntimeError(f"agent {agent_id} produced no result")

        if failed_checks:
            action = pipeline.get("on_dod_failure", {}).get("action", "halt")
            context["_dod_results"][agent_id] = f"fail:{','.join(failed_checks)}"
            events.emit("dod_failure", "dod_validator", {"agent_id": agent_id, "failed_checks": failed_checks})
            notifier.notify("dod_failure", {"agent_id": agent_id, "failed_checks": failed_checks})
            if action == "halt":
                raise RuntimeError(f"DoD failed for {agent_id}: {failed_checks}")
        else:
            context["_dod_results"][agent_id] = "pass"

        out_key = cfg["output_key"]
        context[out_key] = final.content
        context["_costs"][agent_id] = final.cost_usd
        context["_run_spent_usd"] = round(float(context.get("_run_spent_usd", 0.0)) + final.cost_usd, 6)
        context["_tokens"][agent_id] = {
            "input_tokens": final.input_tokens,
            "output_tokens": final.output_tokens,
        }
        context["_timestamps"][f"{agent_id}_end"] = datetime.now(timezone.utc).isoformat()

        ledger.register_agent_cost(
            ledger_data,
            agent_id,
            final.cost_usd,
            final.input_tokens,
            final.output_tokens,
        )

        self._save_agent_output(context["company_id"], context["run_id"], agent_id, out_key, final.content)
        self._append_audit(context, agent_id, step["task"], final, failed_checks)
        if mem_cfg.get("enabled", False):
            memory.append(
                agent_id=agent_id,
                output_key=out_key,
                content=final.content,
                max_entries=int(mem_cfg.get("max_memory_entries", 20)),
            )
        ticketing.create_ticket(
            {
                "run_id": context["run_id"],
                "pipeline_id": context["pipeline_id"],
                "company_id": context["company_id"],
                "agent_id": agent_id,
                "duration_seconds": int(time.time() - started),
                "input": {
                    "task": step["task"],
                    "context_keys_used": cfg.get("input_context_keys", []),
                    "context_size_chars": len(json.dumps(build_agent_input(context, cfg.get("input_context_keys", [])))),
                },
                "output": {
                    "response_preview": final.content[:120],
                    "word_count": len(final.content.split()),
                    "output_key": out_key,
                },
                "model": {
                    "used": final.used_model,
                    "fallback_triggered": final.used_model == cfg["model"]["fallback"],
                    "input_tokens": final.input_tokens,
                    "output_tokens": final.output_tokens,
                    "cost_usd": final.cost_usd,
                    "provider_trace": final.provider_trace,
                },
                "dod": {
                    "status": "pass" if not failed_checks else "fail",
                    "checks": {c["id"]: ("fail" if c["id"] in failed_checks else "pass") for c in cfg.get("definition_of_done", [])},
                    "retries": retries if failed_checks else 0,
                },
            }
        )

    def _save_agent_output(self, company_id: str, run_id: str, agent_id: str, output_key: str, content: str) -> None:
        out_dir = self.root / "storage" / company_id / "outputs" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {"agent_id": agent_id, "output_key": output_key, "content": content}
        (out_dir / f"{agent_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _append_audit(self, context: Dict[str, Any], agent_id: str, task: str, result: Any, failed: Any) -> None:
        audit_dir = self.root / "storage" / context["company_id"] / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "ticket_id": f"TKT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{agent_id}",
            "run_id": context["run_id"],
            "company_id": context["company_id"],
            "agent_id": agent_id,
            "task": task,
            "dod": "pass" if not failed else f"fail:{failed}",
            "tokens": {
                "input": result.input_tokens,
                "output": result.output_tokens,
            },
            "cost_usd": result.cost_usd,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with (audit_dir / "audit.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _save_combined_report(self, context: Dict[str, Any]) -> Path:
        run_id = context["run_id"]
        out_dir = self.root / "storage" / context["company_id"] / "outputs" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        sections = []
        for key in ["ceo_analysis", "product_plan", "technical_plan", "marketing_plan"]:
            if key in context:
                sections.append(f"# {key}\n\n{context[key]}\n")
        report_path = out_dir / "combined_report.md"
        report_path.write_text("\n".join(sections), encoding="utf-8")
        return report_path

    def _company_summary(self, company: Dict[str, Any]) -> str:
        return (
            f"{company['display_name']} | Industry: {company['industry']} | "
            f"Target: {company['target_market']} | Mission: {company['mission']}"
        )

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(path)
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _load_company(self, company_id: str | None = None) -> Dict[str, Any]:
        if company_id:
            p = self.root / "config" / "companies" / f"{company_id}.yaml"
            if p.exists():
                return self._load_yaml(p)
        return self._load_yaml(self.root / "config" / "company.yaml")

    def _agent_monthly_limits(self, company_id: str) -> Dict[str, float]:
        limits: Dict[str, float] = {}
        for aid in ["ceo", "cpo", "cto", "cmo"]:
            p = self.root / "config" / "agents" / f"{aid}.yaml"
            if not p.exists():
                continue
            cfg = self._load_yaml(p)
            if cfg.get("company_id") == company_id:
                limits[aid] = float(cfg.get("budget", {}).get("monthly_limit_usd", 50.0))
        return limits
