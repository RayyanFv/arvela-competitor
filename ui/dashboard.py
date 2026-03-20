from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
import yaml
from dotenv import load_dotenv

from orchestrator.engine import PipelineEngine
from orchestrator.override import OverrideManager


ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _list_runs(company_id: str) -> List[str]:
    base = ROOT / "storage" / company_id / "outputs"
    if not base.exists():
        return []
    runs = [p.name for p in base.iterdir() if p.is_dir() and p.name.startswith("run_")]
    runs.sort(reverse=True)
    return runs


def _list_agent_configs() -> List[Path]:
    return sorted((ROOT / "config" / "agents").glob("*.yaml"))


def _latest_ticket_by_agent(tickets: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for t in tickets:
        aid = t.get("agent_id", "")
        if not aid:
            continue
        prev = latest.get(aid)
        if prev is None or str(t.get("created_at", "")) > str(prev.get("created_at", "")):
            latest[aid] = t
    return latest


def _clone_repo_stats() -> Dict[str, Any]:
    repo = ROOT / "arvela-competitor"
    if not repo.exists():
        return {"exists": False}
    files = [p for p in repo.rglob("*") if p.is_file()]
    return {
        "exists": True,
        "path": str(repo),
        "file_count": len(files),
    }


def _write_new_agent_yaml(payload: Dict[str, Any]) -> str:
    agent_id = payload["agent_id"]
    out = ROOT / "config" / "agents" / f"{agent_id}.yaml"
    if out.exists():
        raise ValueError("agent file already exists")
    out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return str(out)


def render_dashboard() -> None:
    load_dotenv(ROOT / ".env")
    st.set_page_config(page_title="Arvela Company OS", page_icon="A", layout="wide")
    st.title("Arvela Orchestration Dashboard")

    company = _load_yaml(ROOT / "config" / "company.yaml")
    company_id = company.get("company_id", "arvela")
    runs = _list_runs(company_id)
    tickets = _load_jsonl(ROOT / "storage" / company_id / "audit" / "tickets.jsonl")
    budget = _load_json(ROOT / "storage" / "budgets" / f"{company_id}.json")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Company", company.get("display_name", "Unknown"))
    c2.metric("Runs", str(len(runs)))
    c3.metric("Tickets", str(len(tickets)))
    c4.metric("Budget % Used", str(budget.get("totals", {}).get("consumed_pct", 0)))

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "Overview",
            "Org Chart",
            "Run Pipeline",
            "Cost Dashboard",
            "Runs",
            "Audit Log",
            "Hire Agent",
            "Config + Repo",
        ]
    )

    with tab1:
        st.subheader("Mission")
        st.write(company.get("mission", "No mission configured"))
        st.subheader("Recent Runs")
        st.write(runs[:10] if runs else ["No runs yet"])

        if runs:
            latest = runs[0]
            report_path = ROOT / "storage" / company_id / "outputs" / latest / "combined_report.md"
            st.subheader(f"Latest Report: {latest}")
            if report_path.exists():
                txt = report_path.read_text(encoding="utf-8")
                st.code(txt[:4000], language="markdown")
            else:
                st.warning("Latest run has no combined_report.md yet.")

    with tab2:
        st.subheader("Org Chart")
        st.graphviz_chart(
            """
            digraph G {
                rankdir=TB;
                node [shape=box, style=rounded];
                board [label="BOARD (Human)"];
                ceo [label="CEO"];
                cpo [label="CPO"];
                cto [label="CTO"];
                cmo [label="CMO"];
                board -> ceo;
                ceo -> cpo;
                ceo -> cto;
                ceo -> cmo;
            }
            """
        )
        st.subheader("Board Quick Actions")
        ov = OverrideManager(ROOT, company_id)
        a1, a2, a3 = st.columns(3)
        agent_for_action = a1.selectbox("Agent", ["ceo", "cpo", "cto", "cmo"], key="board_agent")
        if a2.button("Pause Agent"):
            st.json(ov.pause_agent(agent_for_action))
        if a3.button("Resume Agent"):
            st.json(ov.resume_agent(agent_for_action))

        latest_by_agent = _latest_ticket_by_agent(tickets)
        rows = []
        for aid in ["ceo", "cpo", "cto", "cmo"]:
            cfg = _load_yaml(ROOT / "config" / "agents" / f"{aid}.yaml")
            b = (budget.get("agents", {}) or {}).get(aid, {})
            lt = latest_by_agent.get(aid, {})
            rows.append(
                {
                    "agent": aid,
                    "model": cfg.get("model", {}).get("primary"),
                    "status": b.get("status", "active"),
                    "spent": b.get("consumed_usd", 0),
                    "limit": b.get("monthly_limit_usd", 0),
                    "last_run": lt.get("created_at", "-")
                }
            )
        st.dataframe(rows, width="stretch")

        st.subheader("Agent Detail Panel")
        detail_agent = st.selectbox("Detail agent", ["ceo", "cpo", "cto", "cmo"], key="detail_agent")
        cfg = _load_yaml(ROOT / "config" / "agents" / f"{detail_agent}.yaml")
        b = (budget.get("agents", {}) or {}).get(detail_agent, {})
        lt = latest_by_agent.get(detail_agent, {})
        recent_tickets = [t.get("ticket_id") for t in tickets[::-1] if t.get("agent_id") == detail_agent][:5]

        st.markdown(f"### {cfg.get('display_name', detail_agent)}")
        d1, d2 = st.columns(2)
        d1.write(f"Model: {cfg.get('model', {}).get('primary', '-')}")
        d2.write(f"Status: {b.get('status', 'active')}")
        st.progress(min(1.0, float(b.get("consumed_pct", 0)) / 100.0), text=f"Budget used: {b.get('consumed_pct', 0)}%")
        st.write(f"Spent: ${b.get('consumed_usd', 0)} / ${b.get('monthly_limit_usd', 0)}")
        st.write(f"Last run: {lt.get('created_at', '-')}")
        st.write(f"DoD status: {lt.get('dod', {}).get('status', '-')}")
        st.write(f"Recent tickets: {', '.join(recent_tickets) if recent_tickets else '-'}")

    with tab3:
        st.subheader("Trigger Pipeline")
        pipelines = sorted((ROOT / "config" / "pipelines").glob("*.yaml"))
        p_map = {p.stem: p for p in pipelines}
        selected = st.selectbox("Pipeline", list(p_map.keys()) if p_map else ["full_run"])
        objective = st.text_area("Objective", height=140, placeholder="Set a specific objective...")
        if st.button("Run Now", type="primary"):
            if not objective.strip():
                st.error("Objective is required.")
            else:
                engine = PipelineEngine(ROOT)
                try:
                    result = engine.run(selected, objective)
                    st.success(f"Run complete: {result['run_id']}")
                    st.write(result["combined_report"])
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")

    with tab4:
        st.subheader("Cost Dashboard")
        if not budget:
            st.info("Budget ledger not initialized yet.")
        else:
            agents_cost = []
            for aid, entry in (budget.get("agents", {}) or {}).items():
                agents_cost.append(
                    {
                        "agent": aid,
                        "spent_usd": entry.get("consumed_usd", 0),
                        "limit_usd": entry.get("monthly_limit_usd", 0),
                        "used_pct": entry.get("consumed_pct", 0),
                        "runs": entry.get("runs_this_month", 0),
                        "status": entry.get("status", "active"),
                    }
                )
            st.dataframe(agents_cost, width="stretch")
            st.json(budget.get("totals", {}))

    with tab5:
        st.subheader("Run Explorer")
        if not runs:
            st.info("No runs found.")
        else:
            run_id = st.selectbox("Select run", runs)
            run_dir = ROOT / "storage" / company_id / "outputs" / run_id
            files = sorted([p.name for p in run_dir.glob("*.json")])
            st.write("Files:", files)
            report = run_dir / "combined_report.md"
            if report.exists():
                text = report.read_text(encoding="utf-8")
                st.download_button("Download combined report", text, file_name=f"{run_id}_combined_report.md")
                st.code(text[:8000], language="markdown")

    with tab6:
        st.subheader("Audit Log")
        if not tickets:
            st.info("No tickets found.")
        else:
            f_agent = st.selectbox("Filter agent", ["all", "ceo", "cpo", "cto", "cmo"], key="flt_agent")
            f_run = st.selectbox("Filter run", ["all"] + runs, key="flt_run")
            rows = []
            for t in tickets[-200:][::-1]:
                if f_agent != "all" and t.get("agent_id") != f_agent:
                    continue
                if f_run != "all" and t.get("run_id") != f_run:
                    continue
                rows.append(
                    {
                        "ticket_id": t.get("ticket_id"),
                        "run_id": t.get("run_id"),
                        "agent": t.get("agent_id"),
                        "model": t.get("model", {}).get("used"),
                        "dod": t.get("dod", {}).get("status"),
                        "cost": t.get("model", {}).get("cost_usd"),
                        "created_at": t.get("created_at"),
                    }
                )
            st.dataframe(rows, width="stretch")
            if rows:
                with st.expander("Show latest matching ticket JSON"):
                    for t in tickets[::-1]:
                        if (f_agent == "all" or t.get("agent_id") == f_agent) and (f_run == "all" or t.get("run_id") == f_run):
                            st.json(t)
                            break

    with tab7:
        st.subheader("Hire Agent")
        with st.form("hire_agent_form"):
            role_id = st.text_input("Role ID", value="custom_qa_engineer")
            display_name = st.text_input("Display Name", value="QA Engineer")
            reports_to = st.selectbox("Reports To", ["ceo", "cpo", "cto", "cmo"], index=2)
            model_primary = st.text_input("Primary Model", value="deepseek/deepseek-r1:free")
            monthly_cap = st.number_input("Monthly Cap (USD)", min_value=1.0, value=30.0, step=1.0)
            system_prompt = st.text_area(
                "System Prompt",
                value="IDENTITY: You are a QA Engineer. Output test plans and bug risks.",
                height=120,
            )
            submit_hire = st.form_submit_button("Hire Agent")

        if submit_hire:
            payload = {
                "agent_id": role_id,
                "display_name": display_name,
                "version": "1.0.0",
                "enabled": True,
                "company_id": company_id,
                "model": {
                    "primary": model_primary,
                    "fallback": "meta-llama/llama-3.3-70b-instruct:free",
                    "temperature": 0.4,
                    "max_tokens": 1200,
                    "timeout_seconds": 120,
                },
                "role": {
                    "title": display_name,
                    "reports_to": reports_to,
                    "direct_reports": [],
                    "scope": "Custom specialist scope",
                    "extended_capabilities": ["analysis", "execution"],
                },
                "system_prompt": system_prompt,
                "input_context_keys": ["objective", "company_context"],
                "output_key": f"{role_id}_output",
                "definition_of_done": [
                    {"id": "output_complete", "check": "present", "value": None, "required": True},
                    {"id": "min_length", "check": "min_words", "value": 120, "required": True},
                ],
                "budget": {
                    "monthly_limit_usd": float(monthly_cap),
                    "per_run_limit_usd": 2.0,
                    "alert_threshold_pct": 80,
                    "on_limit_reached": "escalate_to_ceo",
                },
                "heartbeat": {"enabled": False, "schedule": "0 10 * * 1", "trigger_on": [], "max_runs_per_day": 2},
                "memory": {"enabled": False, "keys_to_persist": [f"{role_id}_output"], "max_memory_entries": 10},
                "audit": {
                    "log_full_prompt": True,
                    "log_full_response": True,
                    "log_token_usage": True,
                    "log_cost": True,
                    "retention_days": 90,
                },
            }
            try:
                out = _write_new_agent_yaml(payload)
                st.success(f"Agent created: {out}")
            except Exception as e:
                st.error(f"Failed to create agent: {e}")

    with tab8:
        st.subheader("Agent Config")
        agents = _list_agent_configs()
        if not agents:
            st.info("No agent config files found.")
        else:
            selected_cfg = st.selectbox("Agent file", [p.name for p in agents])
            cfg_path = ROOT / "config" / "agents" / selected_cfg
            cfg = _load_yaml(cfg_path)
            st.json(cfg)

        st.subheader("Budget Ledger")
        if budget:
            st.json(budget)
        else:
            st.info("Budget ledger not initialized yet.")

        st.subheader("Cloned Repo Explorer")
        repo_stats = _clone_repo_stats()
        if not repo_stats.get("exists"):
            st.warning("Repository arvela-competitor is not cloned yet.")
        else:
            st.write(f"Path: {repo_stats['path']}")
            st.write(f"Files: {repo_stats['file_count']}")
            sample = sorted([str(p.relative_to(ROOT)) for p in (ROOT / "arvela-competitor").glob("**/*") if p.is_file()])[:50]
            st.code("\n".join(sample), language="text")


def summary(root: Path) -> dict:
    company = (root / "config" / "company.yaml").read_text(encoding="utf-8")
    return {
        "company_config_loaded": bool(company),
        "note": "Run with: streamlit run ui/dashboard.py",
    }


if __name__ == "__main__":
    render_dashboard()
