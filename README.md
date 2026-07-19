<div align="center">

<img src="./frontend/public/brand/forefold-icon.png" alt="WHAT IF WHAT IF icon" width="180"/>

# WHAT IF WHAT IF

**One report. Many possible futures.**

## Upload Evidence, Rehearse What Happens Next

Turn public research and internal knowledge into branching simulations. Test decisions across millions of agents before committing in the real world.

</div>

> [!IMPORTANT]
> **License:** WHAT IF WHAT IF is distributed under the [GNU Affero General Public License v3](./LICENSE). Network operators must configure `VITE_SOURCE_CODE_URL` to the complete corresponding source for the exact version they serve. See [NOTICE](./NOTICE) for copyright, warranty, and non-endorsement details.

## ⚡ Overview

**WHAT IF WHAT IF** is a multi-agent decision simulation engine. It extracts seed information from uploaded evidence, constructs parallel digital worlds, and lets agents with independent personalities, memory, and behavioral logic interact. You can test interventions across those possible futures and identify decisions that remain resilient.

WHAT IF WHAT IF carries every completed simulation into one durable decision workflow: the finished report is analyzed for decision paths and uncertainty, sharpened by a bounded set of high-value confidential internal facts, and regenerated as an executive decision report before optional interaction.

> You only need to: Upload seed materials (data analysis reports or interesting novel stories) and describe your prediction requirements in natural language</br>
> WHAT IF WHAT IF will return: A detailed simulation report, an interactive parallel world, and a bounded decision-refinement workflow.

### Our Vision

WHAT IF WHAT IF creates a swarm-intelligence mirror of the evidence you provide. By capturing the collective emergence triggered by individual interactions, it expands traditional scenario analysis:

- **At the Macro Level**: We are a rehearsal laboratory for decision-makers, allowing policies and public relations to be tested at zero risk
- **At the Micro Level**: We are a creative sandbox for individual users — whether deducing novel endings or exploring imaginative scenarios, everything can be fun, playful, and accessible

From serious predictions to playful simulations, we let every "what if" see its outcome, making it possible to predict anything.

## 🔄 Continuous Decision Workflow

1. **Graph Building**: Seed extraction & Individual/collective memory injection & GraphRAG construction
2. **Environment Setup**: Entity relationship extraction & Persona generation & Agent configuration injection
3. **Simulation**: Dual-platform parallel simulation & Auto-parse prediction requirements & Dynamic temporal memory updates
4. **Initial Report**: ReportAgent synthesizes the ontology, graph evidence, and simulation behavior
5. **Decision-Gap Analysis**: WHAT IF WHAT IF reads the completed report, extracts competing paths, and ranks private questions with the legacy Question Priority Score
6. **Bounded Private-Fact Refinement**: WHAT IF WHAT IF asks at most four questions above the Question Priority threshold, keeps answers local, and visibly strengthens, weakens, or prunes affected branches
7. **Final Decision Report**: The engine records targeted re-evaluations, stop conditions, rejected alternatives, remaining uncertainty, and a complete audit trail
8. **Optional Interaction**: Chat with agents or ReportAgent only after the refined decision report is available

The previously imported token-saving controls remain part of this primary simulation workflow:

| Simulation mode | Default platform | Round cap | Active-agent cap | Context guard |
| --- | --- | ---: | ---: | ---: |
| Preview | Twitter | 40 | 10 | 180,000 tokens |
| Balanced | Parallel | 80 | 18 | 220,000 tokens |
| Full Fidelity | Parallel | Generated scenario | No hard cap | 240,000 tokens |

Preview and Balanced also cap agent activity per hour; every mode stops repeated context-overflow attempts through the deterministic context guard. Tool-driven CAMEL Chat Completions calls automatically use `reasoning_effort=none` for compatibility, while non-tool calls retain the selected effort. Real attempted, successful, and failed model requests determine whether a simulation is completed, degraded, or failed.

```text
Seed material
  -> ontology -> GraphRAG -> OASIS multi-agent simulation
  -> initial simulation report
  -> competing paths and uncertainty extracted from that report
  -> at most four material private questions (legacy Question Priority Score)
  -> confidential internal fact stored locally
  -> targeted branch re-evaluation and visible pruning
  -> final executive decision report and audit trail
  -> optional interaction
```

The refinement stage launches no additional public research. Its initial question set is fixed at no more than four facts with a Question Priority Score of at least 45. Re-scoring may reorder or remove those questions, but it cannot add an endless sequence. The engine stops when the set is exhausted, the hard cap is reached, or no remaining fact clears the materiality threshold. Internal evidence is excluded from request logs and default API responses, and private answers use deterministic local interpretation unless model-backed processing is explicitly enabled with user consent.

Saved legacy `/decision/:runId` workspaces remain readable, but `/decision` is no longer a separate import-first product entry. New work continues from a completed report at `/report/:reportId/refinement`.

<details>
<summary><strong>Legacy import compatibility and decision-engine implementation details</strong></summary>

### v2 Local Demo

The v2 demo works without paid API keys or external services.

```bash
# Run from the project root with the existing backend venv
backend/.venv/bin/python backend/scripts/run_v2_demo.py
```

Example output:

```text
documents=1
claims=11
entities=14
relationships=16
hypotheses=3
internal_questions=6
external_llm_calls=0
incremental_model_tokens=0
memo=backend/uploads/v2_runs/<run_id>/decision_memo.md
```

Each run writes an atomic `state.json`, `graph.json`, immutable graph snapshots, `assumptions.json`, `contradictions.json`, `hypotheses.json`, `internal_questions.json`, `internal_evidence.json`, `decision_impacts.json`, `stop_evaluation.json`, `token_usage.json`, append-only `audit_trail.jsonl`, and `decision_memo.md`.

You can also run it through the backend API after starting `npm run backend`:

```bash
curl -X POST http://localhost:5001/api/v2/demo
```

### v2 API

```text
POST /api/v2/run
POST /api/v2/research-pack
POST /api/v2/demo
GET  /api/v2/runs/<run_id>
POST /api/v2/runs/<public_run_id>/fork
GET  /api/v2/runs/<run_id>/lineage
GET  /api/v2/runs/<parent_run_id>/compare/<child_run_id>
GET  /api/v2/runs/<run_id>/internal-questions
POST /api/v2/runs/<run_id>/answers
POST /api/v2/runs/<run_id>/evidence/<evidence_id>/retract
POST /api/v2/runs/<run_id>/stop/evaluate
GET  /api/v2/runs/<run_id>/decision-model
POST /api/v2/runs/<run_id>/decision-model/proposals
POST /api/v2/runs/<run_id>/decision-model/confirm
POST /api/v2/runs/<run_id>/decision-analysis/evaluate
GET  /api/v2/runs/<run_id>/decision-analysis/traces/<trace_id>
POST /api/v2/runs/<run_id>/decision-analysis/evidence-proposals
POST /api/v2/runs/<run_id>/decision-analysis/evidence-proposals/<proposal_id>/confirm
GET  /api/v2/runs/<run_id>/audit
POST /api/v2/runs/<run_id>/question       # source-grounded read-only Q&A
GET  /api/v2/runs/<run_id>/memo.md
```

### Safe decision analysis in shadow mode

A completed public-information run is the immutable baseline. Before any confidential fact, model proposal, or confirmation is stored, the client must fork an owned internal child. The public report never changes; multiple private children can test different internal assumptions against the same baseline.

```text
completed public run (sealed and immutable)
  -> fork owned internal child
  -> store candidate model as an unapproved proposal
  -> human confirms actions, consequence unit, distributions, and utility
  -> exact enumeration or seeded Monte Carlo
  -> internal evidence mapping proposal
  -> human confirms the observation and variable mapping
  -> deterministic distribution update and recalculation
  -> reproducible parent/child comparison
```

The legacy qualitative recommendation remains visible. The deterministic result runs beside it and does not silently replace it.

#### Numeric terms are deliberately separate

| Term | Meaning | May it be used as probability or utility? |
| --- | --- | --- |
| Branch support | Relative qualitative evidence support for an inferred path | No |
| Answer confidence | Whether a private answer is clear enough for the qualitative branch workflow | No; it never performs a Bayesian update |
| Probability | A normalized, human-approved uncertain-variable distribution | Probability only |
| Utility/consequence | A human-approved monetary or utility-point payoff in one explicit unit | Utility only |
| Question Priority Score | `100 × (0.40 sensitivity + 0.30 uncertainty + 0.20 answerability + 0.10 urgency)`; selects which bounded question appears first | No |
| EVPI | Maximum expected value of learning the complete uncertain state perfectly | Derived from the approved model |
| EVPPI | Maximum expected value of perfectly resolving one approved variable or variable group | Derived from the approved model |
| Net information value | EVPPI minus confirmed cash, delay, burden, disclosure-risk, and validation costs | Derived value, not EVSI |
| EVSI | Expected value of a particular imperfect information source | Unavailable until a conditional sampling/likelihood model is approved |

Supported distributions are categorical, discrete points, Bernoulli, beta, normal with optional bounds, triangular, uniform, and fixed/deterministic. Complete finite payoff tables use exact enumeration. Continuous or oversized finite models use bounded, seeded Monte Carlo (10,000 samples by default, 100–100,000 allowed) with convergence and standard-error diagnostics. Dependency declarations fail closed because conditional distributions are not yet supported.

#### Public baseline → private child → confirmed calculation

Fork the baseline:

```bash
curl -X POST http://localhost:5001/api/v2/runs/<public_run_id>/fork \
  -H "Content-Type: application/json" \
  -d '{}'
```

Store a proposal. Approval-looking fields in this request are ignored; only the confirmation endpoint can stamp an actor and timestamp.

```bash
curl -X POST http://localhost:5001/api/v2/runs/<child_run_id>/decision-model/proposals \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "id": "launch_decision",
      "version": "1.0.0",
      "question": "Should we choose the safe or risky launch?",
      "consequence_unit": "utility_points",
      "actions": [
        {"id": "safe", "label": "Safe launch"},
        {"id": "risky", "label": "Risky launch"}
      ],
      "uncertain_variables": [{
        "id": "demand",
        "label": "Demand",
        "unit": "state",
        "distribution": {
          "type": "categorical",
          "parameters": {"probabilities": {"low": 0.7, "high": 0.3}},
          "source": "planning estimate pending human confirmation"
        }
      }],
      "utility_model": {
        "type": "utility_points",
        "risk_attitude": "risk_neutral",
        "unit": "utility_points",
        "version": "1.0.0",
        "outcomes": [
          {"action_id": "safe", "state": {"demand": "low"}, "consequence": 40, "consequence_unit": "utility_points"},
          {"action_id": "safe", "state": {"demand": "high"}, "consequence": 40, "consequence_unit": "utility_points"},
          {"action_id": "risky", "state": {"demand": "low"}, "consequence": 0, "consequence_unit": "utility_points"},
          {"action_id": "risky", "state": {"demand": "high"}, "consequence": 100, "consequence_unit": "utility_points"}
        ]
      }
    }
  }'
```

After reviewing the stored proposal, confirm all four independent responsibilities:

```bash
curl -X POST http://localhost:5001/api/v2/runs/<child_run_id>/decision-model/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "<proposal_id>",
    "confirm_actions": true,
    "confirm_consequence_unit": true,
    "confirm_distributions": true,
    "confirm_utility_model": true,
    "seed": 77,
    "sample_count": 10000
  }'
```

The hand-checkable example returns `EU(safe)=40`, `EU(risky)=30`, expected regrets of `18` and `28`, `EVPI=18`, `EVPPI(demand)=18`, and a risky-action switching threshold of `P(high demand)=0.4`. Exact enumeration reports `sample_count=0`; the seed is still recorded, and the full trace is saved separately under the returned `trace_id`.

To reproduce a calculation, retrieve the approved model, verify its SHA-256 `model_hash`, and call the evaluate endpoint with the recorded seed, requested sample count, information costs, EVPPI groups, and method. Exact models reproduce bit-for-bit from the canonical approved inputs; Monte Carlo models additionally require the same calculation-engine version.

```bash
curl -X POST http://localhost:5001/api/v2/runs/<child_run_id>/decision-analysis/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "seed": 77,
    "sample_count": 10000,
    "information_costs": {
      "demand": {"cash_cost": 4, "delay_cost": 2, "organizational_burden": 1, "disclosure_risk_cost": 0, "validation_cost": 1}
    }
  }'
```

An internal answer does not automatically update a probability. A structured observation must reference active child evidence, remain a proposal, and be confirmed through its own endpoint. Unsupported statistical updates preserve the evidence as `not_applied_to_distribution`.

Multipart upload example:

```bash
curl -X POST http://localhost:5001/api/v2/research-pack \
  -F "files=@test_inputs/v2_demo/cited_deep_research_report.md" \
  -F "question=Should Northstar commit now, run a reversible pilot, or defer?"
```

JSON example:

```bash
curl -X POST http://localhost:5001/api/v2/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Inline Demo",
    "question": "Should we enter this market now, stage a pilot, or defer?",
    "documents": [
      {
        "filename": "deep-research.json",
        "title": "Market Entry Deep Research",
        "sections": [{"title": "Evidence", "text": "Demand grew 18% year over year [Source 1]."}],
        "citations": [{"id": "Source 1", "title": "Fictional market data", "url": "https://example.com/market-data"}]
      }
    ]
  }'
```

Submit the currently requested internal fact:

```bash
curl -X POST http://localhost:5001/api/v2/runs/<run_id>/answers \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "<requested-question-id>",
    "answer": "The pilot budget is approved and a named operating owner is available.",
    "confidential": true
  }'
```

### v2 Environment Variables

The local branch-refinement engine does not require external services. `npm run backend` can start it when core Graphiti/OASIS credentials are absent (with a warning); set `STRICT_STARTUP_VALIDATION=true` when a core simulation deployment should fail closed. Confidential answers are persisted in the local case, redacted from request logs **and default API responses**, and marked `outbound_external_use=false`. There is no raw-answer reveal endpoint and no code path that sends them back into Deep Research. Run directories use owner-only `0700` permissions and case files use `0600` on platforms that support POSIX modes.

The backend binds to `127.0.0.1` by default, the Compose ports are loopback-only, and browser CORS defaults to loopback origins. If you intentionally expose the API beyond the local machine, configure a v2 key and require it through your proxy:

```env
# Required for direct non-loopback v2 access
V2_API_KEY=replace-with-a-long-random-secret

# Set true when a reverse proxy makes external traffic appear to be loopback
V2_REQUIRE_AUTH=true

# Optional comma-separated browser origins for a trusted deployed UI
V2_CORS_ORIGINS=https://decision.example.com

# Local import abuse guard (requests per window)
V2_RUN_RATE_LIMIT=12
V2_RATE_LIMIT_WINDOW_SECONDS=60
```

Authenticated direct API calls accept `Authorization: Bearer <V2_API_KEY>`. The shared key is a local/single-team safety boundary, not multi-tenant authorization; place internet-facing deployments behind your organization’s authenticated reverse proxy and storage controls.

`CONFIDENTIAL_STORAGE_MODE=local_development` stores each raw confidential answer once in an owner-only local artifact and keeps only a reference/redaction marker in canonical and derived state. This is plaintext local-development storage, not production encryption. Production must use `CONFIDENTIAL_STORAGE_MODE=disabled` until an audited key-management/encryption integration and a real identity provider are supplied; confidential writes then fail closed. Legacy Deep Research endpoints default to `410 Gone` through `ENABLE_LEGACY_DEEP_RESEARCH=false`, and the central private-data guard rejects internal evidence in web-search, external-job, prompt, and unrestricted-log payloads.

### v2 Project Structure

```text
backend/app/v2/schemas.py              Typed v2 objects
backend/app/v2/research_ingestion.py   Upload/path/inline document ingestion
backend/app/v2/extraction.py           Provenance-preserving sourced-claim extraction
backend/app/v2/decision.py             Assumptions, hypotheses, question priority, answer impact, pruning, stop logic
backend/app/decision_analysis/         Approved decision schemas, exact/Monte Carlo math, regret, EVPI, and EVPPI
backend/app/v2/decision_analysis.py    Human-confirmed bridge from private child runs to the calculation engine
backend/app/v2/report.py               Executive decision memo generation
backend/app/v2/qa.py                   Follow-up Q&A with citations
backend/app/v2/pipeline.py             End-to-end orchestration
backend/app/api/v2.py                  Flask API routes
frontend/src/views/DecisionWorkspaceView.vue  Integrated research and decision-refinement workbench
test_inputs/v2_demo/                   Fictional Deep Research demo packs
```

### v2 Limitations and Roadmap

- Current extraction and answer interpretation are deterministic heuristics so the workflow is inspectable and token-free.
- Question Priority Score is a prioritization heuristic used only to order bounded questions; it is not EVPI or EVPPI.
- Branch support is relative decision support, not a calibrated probability.
- Decision paths are inferred from explicit alternatives in the decision question and scored from imported evidence. A branch is pruned only by high-confidence evidence that explicitly disqualifies it; a score gap alone only weakens it.
- Questions must be answered in current Question Priority order. Ambiguous or low-confidence answers are retained for audit but do not resolve a question, move a branch, or trigger stopping.
- The decision layer never invents external URLs. If an imported report lacks direct source links, WHAT IF WHAT IF labels the provenance as a report-only anchor.
- Targeted private-fact re-evaluation reuses the completed Graphiti/OASIS evidence lineage without simulating a second public world.

</details>

## 🚀 Quick Start

### Option 1: Source Code Deployment (Recommended)

#### Prerequisites

| Tool | Version | Description | Check Installation |
|------|---------|-------------|-------------------|
| **Node.js** | 18+ | Frontend runtime, includes npm | `node -v` |
| **Python** | ≥3.11, ≤3.12 | Backend runtime | `python --version` |
| **uv** | Latest | Python package manager | `uv --version` |

#### 1. Configure Environment Variables

```bash
# Copy the example configuration file
cp .env.example .env

# Edit the .env file and fill in the required API keys
```

**Required Environment Variables:**

```env
OPENAI_API_KEY=your_openai_api_key
LLM_API_KEY=${OPENAI_API_KEY}
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-5.4-mini
LLM_REASONING_EFFORT=low

GRAPH_BACKEND=graphiti
GRAPHITI_DRIVER=falkordb
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
GRAPHITI_TELEMETRY_ENABLED=false
SEMAPHORE_LIMIT=3

# Must point to the exact corresponding source served to remote users.
VITE_SOURCE_CODE_URL=https://source.example.com/what-if-what-if
```

`ZEP_API_KEY` is no longer needed. WHAT IF WHAT IF uses self-hosted Graphiti with OpenAI for LLM and embedding work.

#### 2. Install Dependencies

```bash
# One-click installation of all dependencies (root + frontend + backend)
npm run setup:all
```

Or install step by step:

```bash
# Install Node dependencies (root + frontend)
npm run setup

# Install Python dependencies (backend, auto-creates virtual environment)
npm run setup:backend
```

The backend uses `uv sync` because Graphiti and OASIS currently disagree on the exact `neo4j` driver pin; the backend `pyproject.toml` contains a resolver override for this.

#### Local Graphiti Setup

Graphiti uses a local graph database. The default backend is FalkorDB.

```bash
# Start FalkorDB locally
docker run -p 6379:6379 -p 3002:3000 -it --rm falkordb/falkordb:latest

# Or use the compose helper profile
docker compose --profile graphiti up -d falkordb
```

FalkorDB exposes the Redis protocol on `6379` and the web UI on `3002`. The frontend uses `3000`.

#### 3. Start Services

```bash
# Start both frontend and backend (run from project root)
npm run dev
```

**Service URLs:**
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

**Start Individually:**

```bash
npm run backend   # Start backend only
npm run frontend  # Start frontend only
```

Run the Graphiti smoke test:

```bash
cd backend
uv run python scripts/test_graphiti_smoke.py
# or, if using pip/venv:
python scripts/test_graphiti_smoke.py
```

End-to-end test flow:

1. Upload a PDF/TXT/MD file.
2. Generate ontology.
3. Build graph.
4. Create simulation.
5. Prepare simulation.
6. Optionally run simulation.
7. Generate report.

### Option 2: Docker Deployment

```bash
# 1. Configure environment variables (same as source deployment)
cp .env.example .env

# 2. Build this checkout and start the core simulation stack, including FalkorDB
docker compose --profile graphiti up -d
```

Reads `.env` from root directory by default, maps ports `3000 (frontend) / 5001 (backend)`

For legacy deterministic import-run compatibility alone, `docker compose up -d` is sufficient and does not start FalkorDB.

## 📄 Acknowledgments

The simulation engine is powered by **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)**. We thank the CAMEL-AI contributors for their open-source work.
