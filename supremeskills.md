# ARVELA ORCHESTRATION SYSTEM
## Master Reference v2.0 — AI Company OS

> **For AI agents reading this file:** This is your source of truth. Read fully before acting. Do not hallucinate missing sections. If a value is marked `[REQUIRED]`, it must be set before the pipeline runs. Token-efficient: every word here is load-bearing.

---

## INDEX

```
§1  System Philosophy
§2  Architecture
§3  Core Agent Roster (C-Suite)
§4  Agent Config Schema
§5  Pipeline Engine
§6  Org Chart & Hierarchy
§7  Heartbeat System
§8  Budget & Cost Control
§9  Ticket & Audit System
§10 Governance & Override
§11 Multi-Company Isolation
§12 Hiring Custom Agents
§13 Interface Specification (UI)
§14 Mobile Interface
§15 Implementation Roadmap
§16 Token Efficiency Rules
```

---

## §1 SYSTEM PHILOSOPHY

**What this is:** A self-governing company of AI agents with real hierarchy, real budgets, real accountability, and a human board that can override anything at any time.

**What this is not:** A chatbot wrapper. A prompt chain. A demo.

**Core axioms:**

1. **Every agent has a boss.** No agent acts without reporting lines. The org chart is enforced by the system, not by honor.
2. **Every task traces to mission.** Agents cannot take actions that don't connect to a configured company objective.
3. **Every decision is auditable.** Full tool-call trace, token count, cost, timestamp, outcome — permanently stored.
4. **Budgets are hard limits.** Not soft warnings. Not notifications. Hard stops.
5. **The human is the board.** Approve hires, override strategy, pause any agent, terminate pipelines — at any time, from anywhere.
6. **Agents are pluggable.** Any model, any runtime. If it accepts a prompt and returns a response, it can be hired.

**Design target:** One operator manages a portfolio of autonomous companies from a phone.

---

## §2 ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                                │
│  Org Chart Engine · Budget Ledger · Governance Layer · Audit Log    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │          ORCHESTRATOR ENGINE         │
          │  Pipeline runner · Context bus       │
          │  DoD validator · Heartbeat scheduler │
          │  Ticket system · Override handler    │
          └──────────────────┬──────────────────┘
                             │
     ┌───────────────────────▼───────────────────────┐
     │                 AGENT LAYER                   │
     │  CEO · CPO · CTO · CMO + Custom agents        │
     │  Each: role config · budget · DoD · KPI       │
     └───────────────────────┬───────────────────────┘
                             │
     ┌───────────────────────▼───────────────────────┐
     │               RUNTIME LAYER                   │
     │  OpenRouter · Direct Anthropic · OpenAI       │
     │  Local (Ollama) · Any HTTP endpoint           │
     └───────────────────────┬───────────────────────┘
                             │
     ┌───────────────────────▼───────────────────────┐
     │               STORAGE LAYER                   │
     │  outputs/  · memory/  · audit/  · budgets/    │
     │  JSON-based · append-only audit log           │
     └───────────────────────────────────────────────┘
```

### Directory Structure

```
arvela-ai-os/
├── main.py                    ← CLI entry point
├── orchestrator/
│   ├── engine.py              ← pipeline runner
│   ├── context_bus.py         ← context passing
│   ├── dod_validator.py       ← DoD enforcement
│   ├── heartbeat.py           ← scheduled runs
│   └── override.py            ← governance hooks
├── agents/
│   ├── base_agent.py          ← abstract base
│   ├── ceo_agent.py
│   ├── cpo_agent.py
│   ├── cto_agent.py
│   └── cmo_agent.py
├── config/
│   ├── company.yaml           ← company context (global)
│   ├── agents/                ← one YAML per agent
│   │   ├── ceo.yaml
│   │   ├── cpo.yaml
│   │   ├── cto.yaml
│   │   └── cmo.yaml
│   └── pipelines/             ← one YAML per pipeline
│       ├── full_run.yaml
│       ├── product_sprint.yaml
│       └── gtm_only.yaml
├── storage/
│   ├── outputs/               ← per-run agent outputs
│   ├── memory/                ← cross-run persistent memory
│   ├── audit/                 ← immutable audit log
│   └── budgets/               ← budget ledger
└── ui/
    ├── dashboard.py           ← Streamlit UI (optional)
    └── mobile_api.py          ← REST API for mobile
```

---

## §3 CORE AGENT ROSTER — C-SUITE

> These four agents cover the full operating surface of a company. Each is a generalist at C-level depth — not a narrow specialist. They are the minimum viable executive team.

---

### CEO — Chief Executive Officer

**Scope:** Strategic direction · company health · cross-functional alignment · board reporting · resource allocation · existential risk management

**Beyond the title:**
- Runs OKR cycles (set, review, grade)
- Detects misalignment between CPO/CTO/CMO outputs
- Makes Go/No-Go on all major initiatives
- Manages hiring decisions (when to add custom agents)
- Competitive intelligence synthesis
- Investor/stakeholder narrative (if applicable)

**Model:** `meta-llama/llama-3.3-70b-instruct:free` | fallback: `mistralai/mistral-7b-instruct:free`
**Temperature:** 0.3 (decisive, consistent)
**Budget cap:** $60/month
**Heartbeat:** Weekly or on-trigger

**System Prompt:**
```
IDENTITY: You are the CEO of {company_name}. You are not an assistant. You are a decision-maker.

COMPANY: {company_context}

OPERATING RULES:
- Every output must contain a decision or a clear recommendation. No analysis without conclusion.
- You receive context from all other agents. You synthesize, not repeat.
- You flag misalignment between divisions. You resolve it.
- You speak in clear, direct language. No corporate filler.
- You track OKRs. Every response references at least one active OKR.
- You do NOT write code. You do NOT design UI. You set direction and hold others accountable.

THINKING PROTOCOL:
1. What is the current state? (facts only)
2. What is the desired state? (from mission/OKR)
3. What is the gap?
4. What decision closes the gap fastest?
5. What is the risk of that decision?
6. What is the risk of NOT deciding?

OUTPUT FORMAT (always):
## Strategic Summary
[2-4 paragraphs: situation, opportunity, threat]

## Decision
[Single clear statement: Go / No-Go / Redirect + why]

## Top 3 Priorities (this sprint)
1. [priority] — [owner agent] — [success metric]
2. ...
3. ...

## Risks
- [risk]: [mitigation]

## OKR Status
[current OKR + grade + trend]

## Open Questions
[questions for other agents that block decision-making]
```

**DoD:**
```yaml
- strategic_summary: min_words=150, required=true
- decision_stated: keywords=["go","no-go","proceed","redirect","lanjutkan","tunda"], required=true
- priorities_count: exactly=3, required=true
- risk_listed: min=1, required=true
- okr_referenced: required=true
```

**KPI:**
```yaml
- word_count: min=300, max=900
- decision_binary: must_be_present=true
- priorities: exactly=3
- risks: min=1
- okr_items: min=1
```

---

### CPO — Chief Product Officer

**Scope:** Product strategy · roadmap · user research · feature prioritization · acceptance criteria · pricing · integrations

**Beyond the title (CPO is also):** Product Manager · Market Researcher · Business Analyst · UX Strategist
- Market research & competitive teardowns
- User persona + JTBD mapping
- RICE/ICE feature scoring
- Pricing & packaging design
- Integration partner strategy (BPJS, Talenta, Mekari, etc.)
- Product analytics interpretation (DAU, retention, funnel)

**Model:** `meta-llama/llama-3.3-70b-instruct:free` | fallback: `google/gemma-3-27b-it:free`
**Temperature:** 0.4
**Budget cap:** $50/month
**Heartbeat:** Per sprint (2-week cycle) or on CEO trigger

**System Prompt:**
```
IDENTITY: You are the CPO of {company_name}. You think in systems, users, and numbers.

COMPANY: {company_context}
CEO CONTEXT: {ceo_analysis}

OPERATING RULES:
- You read CEO output first. Your product plan must serve the CEO's stated priorities.
- You think about users before features. No feature without a user story.
- You score everything. No unscored feature enters the backlog.
- You flag technical questions for CTO. You do not guess at feasibility.
- You own the roadmap. You can push back on CEO priorities if user data contradicts them — but show the data.

SCORING SYSTEM (RICE):
- Reach: How many users in 90 days? (1-10)
- Impact: How much does it move the key metric? (1-10)
- Confidence: How certain are you? (1-10)
- Effort: Engineering weeks? (1-10, where 10 = very high effort)
- RICE Score = (R × I × C) / E

COMPETITIVE CONTEXT:
- Job Posting: Glints, Kalibrr, LinkedIn Jobs
- Assessment: Talentics, Aon, cut-e
- HRIS: Mekari, Talenta, Kerjoo, Gadjian

OUTPUT FORMAT (always):
## Market Insight
[1-2 paragraphs: what competitors miss, what users actually want]

## Feature Prioritization
| Feature | R | I | C | E | RICE | Sprint |
|---------|---|---|---|---|------|--------|

## Top Priority: User Stories
### Story 1: [title]
As a [persona], I want [action] so that [outcome].
**Acceptance Criteria:**
- [ ] criterion 1
- [ ] criterion 2
- [ ] criterion 3

## Open Questions for CTO
1. [technical question]

## Metrics to Watch
- [metric]: current=[x], target=[y]
```

**DoD:**
```yaml
- market_insight: min_words=100, required=true
- feature_table: min_rows=3, required=true
- rice_scores: all_columns_filled=true, required=true
- user_stories: min=2, required=true
- acceptance_criteria: min_per_story=3, required=true
```

**KPI:**
```yaml
- features_scored: min=3
- rice_completeness: 100%
- stories_written: min=2
- ac_per_story: min=3
- ceo_alignment: target=80%
```

---

### CTO — Chief Technology Officer

**Scope:** Technical architecture · implementation · code quality · QA · security · DevOps · infrastructure · tech debt

**Beyond the title (CTO is also):** Lead Engineer · QA Lead · System Analyst · Security Reviewer · DevOps
- Reviews actual codebase when provided
- Writes implementation task breakdowns (real tasks with file paths)
- Flags Indonesian data compliance (PDP UU No. 27/2022)
- Evaluates third-party APIs and vendors
- Owns tech debt register

**Model:** `deepseek/deepseek-r1:free` (best for code reasoning) | fallback: `meta-llama/llama-3.3-70b-instruct:free`
**Temperature:** 0.2 (precise, deterministic)
**Budget cap:** $60/month
**Heartbeat:** Per sprint or on CPO trigger

**System Prompt:**
```
IDENTITY: You are the CTO of {company_name}. You are responsible for everything technical. You do not guess. You reason from first principles.

COMPANY: {company_context}
CEO CONTEXT: {ceo_analysis}
PRODUCT CONTEXT: {product_plan}
STACK: Next.js (React), TypeScript, PostgreSQL, REST/tRPC API, VPS deployment

OPERATING RULES:
- Answer every open question from CPO. No question left unanswered.
- Give real file paths, real component names, real API routes — not abstract descriptions.
- Score tech debt by severity: P0 (blocks shipping) / P1 (degrades quality) / P2 (cleanup later).
- Never over-engineer. Simplest solution that ships is the right solution.
- Own Indonesian PDP compliance for all employee data.
- Estimate in hours, not story points. Be honest about uncertainty.

ARCHITECTURE DECISION RECORD FORMAT:
- Context: [what triggered this decision]
- Options considered: [list]
- Decision: [what we chose]
- Consequences: [impact on codebase]

OUTPUT FORMAT (always):
## Architecture Decision
[ADR format above]

## Implementation Tasks
| # | Task | File/Component | Est. Hours | Depends On |
|---|------|----------------|-----------|------------|

## Tech Debt Register (this sprint)
| ID | Description | Severity | Impact if ignored |
|----|-------------|----------|-------------------|

## QA Checklist
### [Feature Name]
- [ ] Unit: [what]
- [ ] Integration: [what]
- [ ] E2E: [what]
- [ ] Manual: [what]

## Security & Compliance
- PDP flag: [yes/no + detail]
- Auth concern: [if any]
- Data sensitivity: [classification]

## CPO Questions — Answered
1. Q: [question] → A: [answer]
```

**DoD:**
```yaml
- architecture_decision: present=true, required=true
- task_breakdown: min_tasks=3, hours_estimated=true, required=true
- tech_debt: min=1, severity_labeled=true, required=true
- qa_checklist: min_items=5, required=true
- security_section: present=true, required=true
- cpo_questions_answered: 100%, required=true
```

**KPI:**
```yaml
- tasks_defined: min=3
- hours_estimated: all_tasks=true
- tech_debt_items: min=1
- qa_items: min=5
- cpo_coverage: 100%
```

---

### CMO — Chief Marketing Officer

**Scope:** GTM strategy · demand generation · sales enablement · business development · account management · customer lifecycle

**Beyond the title (CMO is also):** Head of Sales · Business Development Lead · Account Manager · Account Executive · Business Analyst
- Owns ICP definition and keeps it updated
- Writes actual sales scripts and objection responses
- Maps BD partnership opportunities (named Indonesian companies)
- Defines unit economics: CAC, LTV, payback period
- Builds churn early-warning system

**Model:** `meta-llama/llama-3.3-70b-instruct:free` | fallback: `google/gemma-3-27b-it:free`
**Temperature:** 0.5 (creative but grounded)
**Budget cap:** $50/month
**Heartbeat:** Weekly (market moves fast)

**System Prompt:**
```
IDENTITY: You are the CMO of {company_name}. You connect product to revenue. You think in pipelines, not campaigns.

COMPANY: {company_context}
CEO CONTEXT: {ceo_analysis}
PRODUCT CONTEXT: {product_plan}
TECHNICAL CONTEXT: {technical_plan}

OPERATING RULES:
- Read all previous agent outputs. Your GTM must reflect what the product actually does.
- Every channel recommendation must include: audience, message, format, frequency, measurable outcome.
- Every partnership must be a named Indonesian company or category.
- Sales scripts must be in Bahasa Indonesia or bilingual. Indonesian SME buyers speak Indonesian.
- Own CAC and LTV. Track them even if current values are estimates.
- Upsell triggers must be behavioral, not calendar-based.

ICP FIELDS (fill all):
- Industry vertical
- Headcount range
- HR maturity level
- Decision maker title
- Budget range (IDR)
- Top 3 pains
- Deal velocity (avg days to close)

OUTPUT FORMAT (always):
## ICP Card
[all fields above]

## Positioning Statement
[one sentence: For [ICP] who [pain], {company_name} is [category] that [differentiation]. Unlike [alternative], we [proof point].]

## GTM Channel Plan
| Channel | Audience | Message | Format | Frequency | KPI |
|---------|----------|---------|--------|-----------|-----|

## Sales Playbook
### Outreach Cadence (5 steps)
Day 1 / Day 3 / Day 7 / Day 14 / Day 21: [channel + message]

### Qualification (BANT-ID)
- Budget / Authority / Need / Timeline / Indonesia-specific question

### Top 3 Objections
1. "[objection]" → "[response in Bahasa Indonesia]"

## Business Development
| Partner Type | Named Target | Value Exchange | Next Action |
|-------------|-------------|---------------|-------------|

## Account Management Playbook
- Churn signal 1: [behavior] → action: [response]
- Churn signal 2: [behavior] → action: [response]
- Upsell trigger: [behavior] → pitch: [module]

## 90-Day Metrics
| Metric | Current | Target | Owner |
|--------|---------|--------|-------|
| MQL    | [x]     | [y]    | CMO   |
```

**DoD:**
```yaml
- icp_card: all_fields_filled=true, required=true
- positioning_statement: max_sentences=1, required=true
- gtm_channels: min=3, kpi_per_channel=true, required=true
- sales_cadence: steps=5, required=true
- objection_scripts: min=3, required=true
- bd_targets: min=3, named=true, required=true
- metrics_table: min_rows=5, targets_numeric=true, required=true
```

**KPI:**
```yaml
- icp_completeness: 100%
- channels: min=3
- objections: min=3
- bd_partners: min=3
- metrics_with_numbers: min=5
```

---

## §4 AGENT CONFIG SCHEMA

Full YAML schema. All agents follow this structure exactly.

```yaml
# config/agents/{agent_id}.yaml

agent_id: string                    # unique, lowercase, underscore
display_name: string
version: semver                     # e.g. "1.0.0"
enabled: boolean
company_id: string

model:
  primary: string                   # OpenRouter model string
  fallback: string
  temperature: float                # 0.0–1.0
  max_tokens: integer
  timeout_seconds: integer          # default 120

role:
  title: string
  reports_to: string | null         # agent_id of manager, null = CEO
  direct_reports: list[string]      # agent_ids
  scope: string
  extended_capabilities: list[string]

system_prompt: multiline_string
output_format_hint: multiline_string

input_context_keys: list[string]    # keys injected from context bus
output_key: string                  # key this agent writes to context bus

budget:
  monthly_limit_usd: float
  per_run_limit_usd: float
  alert_threshold_pct: integer      # default 80
  on_limit_reached: enum            # stop | alert_only | escalate_to_ceo

definition_of_done:
  - id: string
    description: string
    check: enum                     # min_words | contains_keyword | min_rows
                                    # exactly | present | custom_function
    value: any
    required: boolean

kpi:
  - metric: string
    check: enum                     # min | max | exactly | present | range
    value: any
    label: string

heartbeat:
  enabled: boolean
  schedule: cron_string             # e.g. "0 9 * * 1" = Monday 9am
  trigger_on: list[string]          # event names
  max_runs_per_day: integer

memory:
  enabled: boolean
  keys_to_persist: list[string]
  max_memory_entries: integer       # rolling window

audit:
  log_full_prompt: boolean
  log_full_response: boolean
  log_token_usage: boolean
  log_cost: boolean
  retention_days: integer
```

---

## §5 PIPELINE ENGINE

### Pipeline Config Schema

```yaml
# config/pipelines/{pipeline_id}.yaml

pipeline_id: string
display_name: string
company_id: string
enabled: boolean

objective:
  text: multiline_string            # [REQUIRED] — set per run
  focus_area: string
  horizon: enum                     # sprint | quarter | annual

sequence:
  - step: integer
    agent_id: string
    task: multiline_string
    skip_if: string | null
    timeout_minutes: integer

on_dod_failure:
  action: enum                      # retry | skip | halt | escalate
  max_retries: integer
  retry_prompt_suffix: string       # "Your output missed: {failed_checks}"
  notify_agent: string | null

pipeline_budget:
  max_total_usd: float
  on_exceeded: enum                 # halt | skip_remaining | alert

output:
  save_individual: boolean
  save_combined_report: boolean
  combined_report_format: enum      # markdown | json | both
  output_dir: string
  timestamp_files: boolean
```

### Context Bus Protocol

```python
# Context grows incrementally through pipeline
context = {
    # Set at pipeline start
    "run_id": "run_{timestamp}",
    "company_id": "{company_id}",
    "objective": "{pipeline.objective.text}",
    "company_context": "{config/company.yaml summary}",

    # Each agent appends its output_key after completing
    "ceo_analysis": "...",
    "product_plan": "...",
    "technical_plan": "...",
    "marketing_plan": "...",

    # Auto-populated meta
    "_costs": {"ceo": 0.003, "cpo": 0.002, "cto": 0.006, "cmo": 0.003},
    "_tokens": {"ceo": 1240, "cpo": 980, "cto": 1820, "cmo": 1100},
    "_dod_results": {"ceo": "pass", "cpo": "pass", "cto": "pass", "cmo": "pass"},
    "_timestamps": {"ceo_start": "...", "ceo_end": "...", ...}
}
```

**Key rule:** Each agent receives **only its declared `input_context_keys`** — never the full context object. Enforces information boundaries, reduces token waste.

**Context summarization rule:** Before injecting a previous agent's output as context, summarize to max 400 words. Never pass raw full-length outputs.

### Retry Logic

When DoD fails:
1. Identify which checks failed
2. Append to retry prompt: `"Your previous output failed these checks: {list}. Fix them."`
3. Retry up to `max_retries`
4. On final failure: execute `on_dod_failure.action`

---

## §6 ORG CHART & HIERARCHY

```
                    ┌─────────────────┐
                    │   BOARD (Human) │  ← Full override power
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   CEO AGENT     │  reports_to: null
                    └──┬──────┬──┬───┘
                       │      │  │
             ┌─────────┘  ┌───┘  └───────┐
             │            │              │
    ┌────────▼────┐  ┌────▼────┐  ┌─────▼────┐
    │  CPO AGENT  │  │CTO AGENT│  │CMO AGENT │
    └──────┬──────┘  └────┬────┘  └────┬─────┘
           │              │             │
    Custom agents     Custom agents  Custom agents
    (UX, Research,   (QA, DevOps,   (Sales, BD,
     Analytics)       Security)      Content)
```

### Hierarchy Rules

- Agent only receives tasks from direct manager or board.
- Agent only delegates to direct reports.
- CEO can reassign tasks across divisions.
- Board can inject at any level — creates `BOARD_OVERRIDE` audit event.
- Subordinate DoD failure after max retries escalates to manager automatically.

---

## §7 HEARTBEAT SYSTEM

When a heartbeat fires:
1. Agent checks for pending work (unprocessed tickets, new context, scheduled task)
2. If work exists: runs configured task
3. Outputs go to context bus and storage
4. Result logged to audit

### Heartbeat Config (in agent YAML)

```yaml
heartbeat:
  enabled: true
  schedule: "0 9 * * 1"        # every Monday 9am
  trigger_on:
    - "pipeline_complete"
    - "ceo_decision_changed"
    - "budget_threshold_hit"
    - "dod_failure"
    - "codebase_changed"
    - "new_ticket"
  max_runs_per_day: 3
```

### Event Types

| Event | Triggered By | Default Listeners |
|-------|-------------|-------------------|
| `pipeline_complete` | Orchestrator | CEO, CMO |
| `dod_failure` | DoD validator | Manager agent |
| `budget_threshold` | Budget ledger | CEO |
| `board_override` | Human board | All agents |
| `new_objective` | Human input | CEO |
| `agent_hired` | Human board | CEO, direct manager |
| `codebase_changed` | Git webhook | CTO |
| `new_ticket` | Ticket system | Assigned agent |

---

## §8 BUDGET & COST CONTROL

### Budget Ledger Schema

```json
{
  "company_id": "arvela",
  "period": "2026-03",
  "agents": {
    "ceo": {
      "monthly_limit_usd": 60.00,
      "consumed_usd": 42.00,
      "consumed_pct": 70.0,
      "runs_this_month": 14,
      "avg_cost_per_run": 3.00,
      "token_breakdown": {
        "input_tokens": 284000,
        "output_tokens": 98000
      },
      "status": "active"
    }
  },
  "pipeline_costs": [
    {
      "run_id": "run_20260320_143000",
      "pipeline_id": "full_run",
      "total_cost_usd": 0.018,
      "agents": {"ceo": 0.005, "cpo": 0.004, "cto": 0.006, "cmo": 0.003}
    }
  ],
  "totals": {
    "monthly_limit_usd": 220.00,
    "consumed_usd": 97.00,
    "consumed_pct": 44.1,
    "projected_month_end_usd": 138.00
  }
}
```

### Enforcement Rules

```
Hard rules (not configurable):
- Agent stops immediately when monthly_limit_usd is hit
- Pipeline halts if pipeline_budget.max_total_usd hit mid-run
- Board alert at alert_threshold_pct (default 80%)

Configurable per agent:
on_limit_reached:
  stop          → agent stops all runs until next period
  alert_only    → agent continues, board alerted
  escalate_to_ceo → CEO decides whether to continue
```

### Cost Tracking Granularity

Every run logs: cost per agent · cost per task · cost per pipeline · input vs output tokens · model used (primary vs fallback)

---

## §9 TICKET & AUDIT SYSTEM

Every agent interaction creates an immutable ticket.

### Ticket Schema

```json
{
  "ticket_id": "TKT-20260320-0042",
  "run_id": "run_20260320_143000",
  "pipeline_id": "full_run",
  "company_id": "arvela",
  "agent_id": "cto",
  "status": "complete",
  "created_at": "2026-03-20T14:32:11Z",
  "completed_at": "2026-03-20T14:34:45Z",
  "duration_seconds": 154,
  "input": {
    "task": "Based on product plan, create technical implementation...",
    "context_keys_used": ["ceo_analysis", "product_plan"],
    "context_size_chars": 4820
  },
  "output": {
    "response_preview": "## Architecture Decision\n...",
    "word_count": 612,
    "output_key": "technical_plan"
  },
  "model": {
    "used": "deepseek/deepseek-r1:free",
    "fallback_triggered": false,
    "input_tokens": 1840,
    "output_tokens": 890,
    "cost_usd": 0.0
  },
  "dod": {
    "status": "pass",
    "checks": {
      "architecture_decision": "pass",
      "task_breakdown": "pass",
      "tech_debt": "pass",
      "qa_checklist": "pass",
      "security_section": "pass",
      "cpo_questions_answered": "pass"
    },
    "retries": 0
  },
  "audit_hash": "sha256:abc123..."
}
```

### Audit Rules

- Append-only. No edits, no deletes.
- Every board override logged with: who, what, when, reason.
- Retention: 90 days default, configurable.
- Export: JSON or CSV on demand.

---

## §10 GOVERNANCE & OVERRIDE

The board (human) has supreme authority at all times.

### Board Actions

| Action | Effect | Audit Event |
|--------|--------|-------------|
| `pause_agent(id)` | Agent stops new tasks | `AGENT_PAUSED` |
| `resume_agent(id)` | Agent resumes | `AGENT_RESUMED` |
| `terminate_run(id)` | Kills pipeline mid-run | `RUN_TERMINATED` |
| `override_dod(ticket_id)` | Marks DoD passed manually | `DOD_OVERRIDDEN` |
| `inject_context(key, val)` | Adds to context bus | `CONTEXT_INJECTED` |
| `reset_budget(id)` | Clears monthly consumption | `BUDGET_RESET` |
| `hire_agent(config)` | Registers new agent | `AGENT_HIRED` |
| `fire_agent(id)` | Disables agent permanently | `AGENT_FIRED` |
| `promote_agent(id, new_manager)` | Changes reporting line | `ORG_CHANGE` |

Any override: logs immediately → notifies CEO (unless CEO is target) → takes effect instantly.

---

## §11 MULTI-COMPANY ISOLATION

One deployment, N companies. Complete data isolation.

### Company Config Schema

```yaml
# config/company.yaml
company_id: "arvela"
display_name: "Arvela"
industry: "HR SaaS"
stage: "early_growth"
target_market: "Indonesian companies, 50-500 employees"
product_modules:
  - Job Posting
  - Assessment
  - HRIS Operational
competitors:
  - Glints
  - Talentics
  - Mekari
  - Talenta
  - Kerjoo
mission: "Simplify HR operations for growing Indonesian companies."
okrs:
  - objective: "Achieve product-market fit in HRIS module"
    key_results:
      - "100 paid customers by Q2 2026"
      - "NPS > 40 by Q2 2026"
      - "Churn < 5%/month by Q2 2026"
```

### Isolation Rules

- All storage paths prefixed with `{company_id}/`
- Budget ledgers are per company
- Agents instantiated per company (same config, isolated state)
- Audit logs never cross company boundaries
- Context bus is company-scoped

---

## §12 HIRING CUSTOM AGENTS

Add any specialist agent without touching core code.

### Custom Agent Template

```yaml
# config/agents/custom_{role}.yaml

agent_id: "custom_{role}"
display_name: "{Role Name}"
version: "1.0.0"
enabled: true
company_id: "{company_id}"

model:
  primary: "{model_string}"
  fallback: "meta-llama/llama-3.3-70b-instruct:free"
  temperature: 0.4
  max_tokens: 1500
  timeout_seconds: 120

role:
  title: "{Full Title}"
  reports_to: "{manager_agent_id}"
  direct_reports: []
  scope: "{one line: what this agent owns}"
  extended_capabilities:
    - "{capability 1}"
    - "{capability 2}"

system_prompt: |
  IDENTITY: You are the {title} of {company_name}.

  COMPANY: {company_context}

  OPERATING RULES:
  - [rule 1]
  - [rule 2]
  - You report to {manager_title}. Escalate blockers upward.
  - You communicate with precision. No filler.

  OUTPUT FORMAT (always):
  ## [Section 1]
  [content]

  ## [Section 2]
  [content]

definition_of_done:
  - id: "output_complete"
    description: "All required sections present"
    check: "present"
    required: true
  - id: "min_length"
    check: "min_words"
    value: 150
    required: true

kpi:
  - metric: "word_count"
    check: "range"
    value: [150, 800]
    label: "Output word count"

budget:
  monthly_limit_usd: 30.00
  per_run_limit_usd: 2.00
  alert_threshold_pct: 80
  on_limit_reached: "escalate_to_ceo"

input_context_keys:
  - "{manager_output_key}"

output_key: "custom_{role}_output"

heartbeat:
  enabled: false
  schedule: "0 10 * * 1"
  trigger_on: []
  max_runs_per_day: 2

memory:
  enabled: false
  keys_to_persist: ["custom_{role}_output"]
  max_memory_entries: 10

audit:
  log_full_prompt: true
  log_full_response: true
  log_token_usage: true
  log_cost: true
  retention_days: 90
```

### Pre-Built Custom Agent Roster (activate when needed)

| Agent ID | Reports To | Primary Use |
|----------|-----------|-------------|
| `ux_researcher` | cpo | User interviews, persona research |
| `data_analyst` | cpo | Metrics, funnel, A/B results |
| `qa_engineer` | cto | Test writing, regression, bug reports |
| `devops_agent` | cto | CI/CD, infra, deployment |
| `security_auditor` | cto | PDP compliance, security review |
| `content_writer` | cmo | Blog, LinkedIn, email copy |
| `seo_specialist` | cmo | Keywords, on-page optimization |
| `sales_agent` | cmo | Outbound sequences, follow-up |
| `bd_agent` | cmo | Partnership outreach, deal tracking |
| `hr_specialist` | ceo | Job descriptions, comp benchmarking |
| `finance_analyst` | ceo | Burn rate, unit economics, forecasting |
| `legal_reviewer` | ceo | Contract review, compliance |

---

## §13 INTERFACE SPECIFICATION (UI)

The UI renders system state and routes board actions to the orchestrator API. It does not control agents directly.

### Views

#### Org Chart View
- Visual hierarchy tree (CEO at top)
- Each node: agent name · model · status (active/paused/over-budget) · last run timestamp
- Click node → agent detail panel
- Drag to reassign reporting lines → `ORG_CHANGE` event

#### Agent Detail Panel
```
┌─────────────────────────────────────────────────────┐
│ CTO Agent                          [Pause] [Config] │
│ Model: deepseek/deepseek-r1:free   Status: Active   │
├─────────────────────────────────────────────────────┤
│ Budget                                              │
│ ████████████░░░░  $25 / $60   41.7% remaining      │
│ Projected month-end: $48                            │
├─────────────────────────────────────────────────────┤
│ Last Run    2026-03-20 14:34   Duration: 154s       │
│ DoD Status  ✓ All 6 checks passed   Retries: 0     │
│ Tickets     TKT-0042, TKT-0038, TKT-0031           │
├─────────────────────────────────────────────────────┤
│ KPI (last run)                                      │
│ Tasks defined        5 / min 3    ✓                │
│ Hours estimated      all          ✓                │
│ Tech debt items      2 / min 1    ✓                │
│ QA checklist items   8 / min 5    ✓                │
│ CPO question coverage  100%       ✓                │
└─────────────────────────────────────────────────────┘
```

#### Pipeline Runner
- Select pipeline config
- Set objective text
- Preview agents + estimated cost before running
- Run → streams output in real time (one panel per agent)
- Each panel: agent name · model · live DoD checklist

#### Cost Dashboard
```
┌────────────────────────────────────────────────────────┐
│ March 2026                              arvela.id      │
├────────────────────────────────────────────────────────┤
│ Agent     Model              Spent    Limit   %Used    │
│ CEO       Llama 3.3 70B      $42      $60     70%  ●  │
│ CPO       Llama 3.3 70B      $18      $50     36%  ●  │
│ CTO       DeepSeek R1        $25      $60     42%  ●  │
│ CMO       Llama 3.3 70B      $12      $50     24%  ●  │
├────────────────────────────────────────────────────────┤
│ Total                        $97      $220    44%      │
│ Projected month-end          $138     $220             │
├────────────────────────────────────────────────────────┤
│ Cost by pipeline (this month)                          │
│ full_run          12 runs    $68                       │
│ product_sprint     8 runs    $22                       │
│ gtm_only           4 runs    $7                        │
└────────────────────────────────────────────────────────┘
```

#### Audit Log View
- Filter by: agent · date · event type · run_id
- Expandable rows: full prompt · full response · tool calls
- Export: JSON / CSV
- Board overrides: highlighted amber
- DoD failures: highlighted red

#### Hire Agent Modal
```
┌─────────────────────────────────────────────────────┐
│ Hire New Agent                                      │
├─────────────────────────────────────────────────────┤
│ Role ID      [custom_qa_engineer        ]           │
│ Display Name [QA Engineer               ]           │
│ Reports To   [CTO Agent          ▼      ]           │
│ Model        [deepseek/deepseek-r1:free ▼]          │
│ Monthly Cap  [$ 30.00                   ]           │
│                                                     │
│ System Prompt                                       │
│ [multiline text editor with template pre-filled   ] │
│                                                     │
│ DoD Items    [+ Add check               ]           │
│ ✓ Output present                                   │
│ ✓ Min 150 words                                    │
│                                                     │
│            [Cancel]  [Preview]  [Hire Agent]        │
└─────────────────────────────────────────────────────┘
```

---

## §14 MOBILE INTERFACE

Monitor and intervene from anywhere. All board actions available on mobile.

### Screens

**Home:** Company health at a glance — active agents · budget ring · last pipeline run · pending board actions

**Quick actions (always reachable):** Pause / resume agent · trigger pipeline · view latest output · override DoD · set budget alert

**Push notifications:** Budget 80% threshold · budget limit reached (agent stopped) · DoD failure after max retries · pipeline complete · board action required

### Mobile API (REST)

```
GET  /api/v1/{company_id}/agents
GET  /api/v1/{company_id}/agents/{agent_id}
POST /api/v1/{company_id}/agents/{agent_id}/pause
POST /api/v1/{company_id}/agents/{agent_id}/resume
GET  /api/v1/{company_id}/budgets
GET  /api/v1/{company_id}/pipelines
POST /api/v1/{company_id}/pipelines/{pipeline_id}/run
GET  /api/v1/{company_id}/tickets
GET  /api/v1/{company_id}/tickets/{ticket_id}
POST /api/v1/{company_id}/board/override
```

---

## §15 IMPLEMENTATION ROADMAP

### Phase 0 — Local MVP (Week 1–2)
Goal: Pipeline runs end-to-end. CEO → CPO → CTO → CMO. Outputs saved.

- [ ] `base_agent.py`: OpenRouter call + retry + token logging
- [ ] `engine.py`: load YAML, run sequence, pass context
- [ ] `dod_validator.py`: keyword + word count checks
- [ ] 4 agent YAML configs
- [ ] `full_run.yaml` pipeline config
- [ ] `main.py` CLI: `python main.py --pipeline full_run --objective "..."`
- [ ] JSON output per agent + combined report

**Success criterion:** `python main.py` against arvela codebase produces coherent, DoD-passing outputs from all 4 agents.

### Phase 1 — Budget + Audit (Week 3)
- [ ] Budget ledger (JSON, consumed tracked per run)
- [ ] Hard stop at limit
- [ ] Ticket creation per agent run
- [ ] Append-only audit log

### Phase 2 — Heartbeat + Memory (Week 4)
- [ ] Heartbeat scheduler (APScheduler or systemd)
- [ ] Cross-run memory (persist + inject on next run)
- [ ] Basic event system

### Phase 3 — UI (Week 5–6)
- [ ] Streamlit: org chart · pipeline runner · cost view · audit log
- [ ] Hire agent modal (generates YAML)
- [ ] Real-time output streaming

### Phase 4 — Mobile API + Multi-Company (Week 7–8)
- [ ] FastAPI mobile REST API
- [ ] Company isolation (prefix all paths)
- [ ] Push notification hook (webhook or email)

---

## §16 TOKEN EFFICIENCY RULES

> Written FOR AI agents implementing this system.

**Rule 1 — Read config, don't hallucinate it.**
Before generating output, load the agent's YAML. Never assume a system prompt, DoD, or model.

**Rule 2 — Inject only declared context keys.**
Each agent declares `input_context_keys`. Only those keys go into the prompt. Never pass the full context object.

**Rule 3 — Summarize before passing.**
Summarize previous agent output to max 400 words before injecting as context. Never pass raw full-length outputs.

**Rule 4 — Output format is not optional.**
DoD validator parses structured output. Free-form responses fail DoD and trigger costly retries. Format correctly on the first attempt.

**Rule 5 — DoD failures are expensive.**
Each retry doubles the token cost of that step. Check DoD criteria before finishing output.

**Rule 6 — Temperature discipline.**
Use the configured temperature. CEO: 0.3, CTO: 0.2 for consistent, parseable output. Do not override.

**Rule 7 — No verbose preamble.**
Do not begin with "Certainly!", "Of course!", or any preamble. Begin with the first section header. Every preamble token is wasted money.

**Rule 8 — Memory is a feature, not a crutch.**
If `memory.enabled: true`, check memory before generating. Do not re-derive what was already decided.

---

*End of document. Version 2.0. Last updated: 2026-03-20.*
*This document is the source of truth. When in doubt, refer here.*