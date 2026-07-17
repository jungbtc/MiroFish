<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

<a href="https://trendshift.io/repositories/16144" target="_blank"><img src="https://trendshift.io/api/badge/repositories/16144" alt="666ghj%2FMiroFish | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

简洁通用的群体智能引擎，预测万物
</br>
<em>A Simple and Universal Swarm Intelligence Engine, Predicting Anything</em>

<a href="https://www.shanda.com/" target="_blank"><img src="./static/image/shanda_logo.png" alt="666ghj%2FMiroFish | Shanda" height="40"/></a>

[![GitHub Stars](https://img.shields.io/github/stars/666ghj/MiroFish?style=flat-square&color=DAA520)](https://github.com/666ghj/MiroFish/stargazers)
[![GitHub Watchers](https://img.shields.io/github/watchers/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/watchers)
[![GitHub Forks](https://img.shields.io/github/forks/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/666ghj/MiroFish)

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=flat-square&logo=discord&logoColor=white)](http://discord.gg/ePf5aPaHnA)
[![X](https://img.shields.io/badge/X-Follow-000000?style=flat-square&logo=x&logoColor=white)](https://x.com/mirofish_ai)
[![Instagram](https://img.shields.io/badge/Instagram-Follow-E4405F?style=flat-square&logo=instagram&logoColor=white)](https://www.instagram.com/mirofish_ai/)

[English](./README.md) | [中文文档](./README-ZH.md)

</div>

## ⚡ Overview

**MiroFish** is a next-generation AI prediction engine powered by multi-agent technology. By extracting seed information from the real world (such as breaking news, policy drafts, or financial signals), it automatically constructs a high-fidelity parallel digital world. Within this space, thousands of intelligent agents with independent personalities, long-term memory, and behavioral logic freely interact and undergo social evolution. You can inject variables dynamically from a "God's-eye view" to precisely deduce future trajectories — **rehearse the future in a digital sandbox, and win decisions after countless simulations**.

MiroFish now carries every completed simulation into one durable decision workflow: the initial report is enriched by cited OpenAI Deep Research, sharpened by confidential internal facts, and regenerated as an executive decision report before optional interaction.

> You only need to: Upload seed materials (data analysis reports or interesting novel stories) and describe your prediction requirements in natural language</br>
> MiroFish will return: A detailed prediction report and a deeply interactive high-fidelity digital world

### Our Vision

MiroFish is dedicated to creating a swarm intelligence mirror that maps reality. By capturing the collective emergence triggered by individual interactions, we break through the limitations of traditional prediction:

- **At the Macro Level**: We are a rehearsal laboratory for decision-makers, allowing policies and public relations to be tested at zero risk
- **At the Micro Level**: We are a creative sandbox for individual users — whether deducing novel endings or exploring imaginative scenarios, everything can be fun, playful, and accessible

From serious predictions to playful simulations, we let every "what if" see its outcome, making it possible to predict anything.

## 🌐 Live Demo

Welcome to visit our online demo environment and experience a prediction simulation on trending public opinion events we've prepared for you: [mirofish-live-demo](https://666ghj.github.io/mirofish-demo/)

## 📸 Screenshots

<div align="center">
<table>
<tr>
<td><img src="./static/image/Screenshot/运行截图1.png" alt="Screenshot 1" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图2.png" alt="Screenshot 2" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图3.png" alt="Screenshot 3" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图4.png" alt="Screenshot 4" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图5.png" alt="Screenshot 5" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图6.png" alt="Screenshot 6" width="100%"/></td>
</tr>
</table>
</div>

## 🎬 Demo Videos

### 1. Wuhan University Public Opinion Simulation + MiroFish Project Introduction

<div align="center">
<a href="https://www.bilibili.com/video/BV1VYBsBHEMY/" target="_blank"><img src="./static/image/武大模拟演示封面.png" alt="MiroFish Demo Video" width="75%"/></a>

Click the image to watch the complete demo video for prediction using BettaFish-generated "Wuhan University Public Opinion Report"
</div>

### 2. Dream of the Red Chamber Lost Ending Simulation

<div align="center">
<a href="https://www.bilibili.com/video/BV1cPk3BBExq" target="_blank"><img src="./static/image/红楼梦模拟推演封面.jpg" alt="MiroFish Demo Video" width="75%"/></a>

Click the image to watch MiroFish's deep prediction of the lost ending based on hundreds of thousands of words from the first 80 chapters of "Dream of the Red Chamber"
</div>

> **Financial Prediction**, **Political News Prediction** and more examples coming soon...

## 🔄 Continuous Decision Workflow

1. **Graph Building**: Seed extraction & Individual/collective memory injection & GraphRAG construction
2. **Environment Setup**: Entity relationship extraction & Persona generation & Agent configuration injection
3. **Simulation**: Dual-platform parallel simulation & Auto-parse prediction requirements & Dynamic temporal memory updates
4. **Initial Report**: ReportAgent synthesizes the ontology, graph evidence, and simulation behavior
5. **Public Deep Research**: A durable OpenAI Responses API background job adds current external evidence with preserved citations
6. **Private-Fact Refinement**: MiroFish ranks decision-critical internal questions, keeps answers out of web search, and visibly strengthens, weakens, or prunes affected branches
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
  -> cited OpenAI Deep Research (durable background Responses job)
  -> ranked private questions (explainable Information Value Score)
  -> confidential internal fact stored locally
  -> targeted branch re-evaluation and visible pruning
  -> final executive decision report and audit trail
  -> optional interaction
```

Research jobs are idempotent and resumable: their provider response ID, status, progress, citations, retry state, and cancellation state are persisted with the original project, graph, simulation, and report lineage. Deep Research receives only the initial public/simulation context. Internal evidence is excluded from web-search inputs, request logs, and default API responses. Private answers use deterministic local interpretation unless model-backed processing is explicitly enabled with user consent.

Implementation follows OpenAI's current [Deep Research](https://developers.openai.com/api/docs/guides/deep-research), [background mode](https://developers.openai.com/api/docs/guides/background), and [web search](https://developers.openai.com/api/docs/guides/tools-web-search) guidance: long-running work uses a background Responses job, and returned URL citations remain visible and clickable in the refinement workspace and final report.

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
GET  /api/v2/runs/<run_id>/internal-questions
POST /api/v2/runs/<run_id>/answers
POST /api/v2/runs/<run_id>/stop/evaluate
GET  /api/v2/runs/<run_id>/audit
POST /api/v2/runs/<run_id>/question       # source-grounded read-only Q&A
GET  /api/v2/runs/<run_id>/memo.md
```

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

Authenticated direct API calls accept either `Authorization: Bearer <V2_API_KEY>` or `X-MiroFish-Key: <V2_API_KEY>`. The shared key is a local/single-team safety boundary, not multi-tenant authorization; place internet-facing deployments behind your organization’s authenticated reverse proxy and storage controls.

### v2 Project Structure

```text
backend/app/v2/schemas.py              Typed v2 objects
backend/app/v2/research_ingestion.py   Upload/path/inline document ingestion
backend/app/v2/extraction.py           Provenance-preserving sourced-claim extraction
backend/app/v2/decision.py             Assumptions, hypotheses, IVS, answer impact, pruning, stop logic
backend/app/v2/report.py               Executive decision memo generation
backend/app/v2/qa.py                   Follow-up Q&A with citations
backend/app/v2/pipeline.py             End-to-end orchestration
backend/app/api/v2.py                  Flask API routes
frontend/src/views/DecisionWorkspaceView.vue  Integrated research and decision-refinement workbench
test_inputs/v2_demo/                   Fictional Deep Research demo packs
```

### v2 Limitations and Roadmap

- Current extraction and answer interpretation are deterministic heuristics so the workflow is inspectable and token-free.
- Information Value Score is a prioritization heuristic, not rigorous EVPI.
- Branch support is relative decision support, not a calibrated probability.
- Decision paths are inferred from explicit alternatives in the decision question and scored from imported evidence. A branch is pruned only by high-confidence evidence that explicitly disqualifies it; a score gap alone only weakens it.
- Questions must be answered in current IVS order. Ambiguous or low-confidence answers are retained for audit but do not resolve a question, move a branch, or trigger stopping.
- The decision layer never invents external URLs. If an imported report lacks direct source links, MiroFish labels the provenance as a report-only anchor.
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
```

`ZEP_API_KEY` is no longer needed. MiroFish now uses self-hosted Graphiti with OpenAI for LLM and embedding work.

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

## 📬 Join the Conversation

<div align="center">
<img src="./static/image/QQ群.png" alt="QQ Group" width="60%"/>
</div>

&nbsp;

The MiroFish team is recruiting full-time/internship positions. If you're interested in multi-agent simulation and LLM applications, feel free to send your resume to: **mirofish@shanda.com**

## 📄 Acknowledgments

**MiroFish has received strategic support and incubation from Shanda Group!**

MiroFish's simulation engine is powered by **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)**, We sincerely thank the CAMEL-AI team for their open-source contributions!

## 📈 Project Statistics

<a href="https://www.star-history.com/#666ghj/MiroFish&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&legend=top-left" />
 </picture>
</a>
