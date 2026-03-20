from __future__ import annotations

import argparse
import time
from pathlib import Path

from dotenv import load_dotenv

from orchestrator.engine import PipelineEngine
from orchestrator.heartbeat import HeartbeatScheduler
import yaml


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Arvela AI Company OS - Local MVP")
    p.add_argument("--mode", choices=["run", "api", "heartbeat"], default="run", help="run pipeline, API, or heartbeat service")
    p.add_argument("--pipeline", default="full_run", help="Pipeline ID from config/pipelines")
    p.add_argument("--objective", default="", help="Run objective (required for --mode run)")
    p.add_argument("--host", default="127.0.0.1", help="API host for --mode api")
    p.add_argument("--port", type=int, default=8000, help="API port for --mode api")
    p.add_argument("--company", default="", help="Company ID for run/heartbeat mode")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    load_dotenv(root / ".env")
    if args.mode == "api":
        import uvicorn

        uvicorn.run("ui.mobile_api:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.mode == "heartbeat":
        if args.company:
            p = root / "config" / "companies" / f"{args.company}.yaml"
            company = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
        else:
            company = yaml.safe_load((root / "config" / "company.yaml").read_text(encoding="utf-8"))
        company_id = company.get("company_id", args.company or "arvela")
        scheduler = HeartbeatScheduler(root, company_id)
        agents = []
        for p in (root / "config" / "agents").glob("*.yaml"):
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            if cfg.get("company_id") == company_id:
                agents.append(cfg)

        routes = yaml.safe_load((root / "config" / "heartbeat_routes.yaml").read_text(encoding="utf-8")) or {"routes": {}}

        def _on_fire(agent_id: str) -> None:
            engine = PipelineEngine(root)
            try:
                route = routes.get("routes", {}).get(agent_id, {})
                pipeline_id = route.get("pipeline_id", "full_run")
                tpl = route.get("objective_template", "Heartbeat trigger for {agent_id} ({company_id})")
                objective = tpl.format(agent_id=agent_id, company_id=company_id)
                engine.run(pipeline_id, objective, company_id=company_id)
            except Exception:
                pass

        scheduler.start(agents, on_fire=_on_fire)
        print("Heartbeat service running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            print("Heartbeat service stopped.")
            return 0

    if not args.objective.strip():
        raise ValueError("--objective is required when --mode run")

    engine = PipelineEngine(root)
    result = engine.run(args.pipeline, args.objective, company_id=args.company or None)
    print("Run complete")
    print(f"run_id: {result['run_id']}")
    print(f"combined_report: {result['combined_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
