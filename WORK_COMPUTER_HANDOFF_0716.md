# MiroFish Work-Computer Handoff — July 16

## Branch

```text
feature/newInfo_0716
```

This branch is based on the updated `main` decision-layer release and adds a
follow-up correction: the original ontology and multi-agent decision process is
still the primary product. The Deep Research decision layer is an optional,
token-free extension—not a replacement.

## What is included

- `/` keeps the original PDF/Markdown/TXT upload, model and reasoning controls,
  ontology generation, Graphiti graph build, OASIS agents, simulation, report,
  interaction, and project history.
- `/decision` is a separate Deep Research importer for PDF, Markdown, and JSON.
- `/decision/:runId` is the deterministic decision workspace.
- Preview, Balanced, and Full token-saving modes remain part of the core flow.
- English and Chinese UI copy now describes the decision layer as optional.
- `/health` reports core Graphiti/OASIS readiness separately from the local
  deterministic decision add-on.
- Regression tests protect both workflows from replacing one another again.

## Set up on the work computer

```bash
git fetch origin
git switch feature/newInfo_0716
npm run setup:all
cp .env.example .env
```

Add a real `OPENAI_API_KEY` to `.env`. Keep `.env` local; no credentials are
committed. The supported backend Python versions are 3.11 and 3.12.

For the full ontology and simulation workflow, start FalkorDB and the app:

```bash
docker compose --profile graphiti up -d falkordb
npm run dev
```

Then open `http://localhost:3000`. FalkorDB's UI is at
`http://localhost:3002`, and the backend is at `http://localhost:5001`.

Alternatively, run the complete local Docker stack:

```bash
docker compose --profile graphiti up -d
```

The optional `/decision` workflow can run without FalkorDB. It does not need an
LLM call for its deterministic analysis.

## What remains on the work computer

- Supply the real OpenAI/API credentials in `.env`.
- Run the Graphiti smoke test against the work computer's FalkorDB instance:

  ```bash
  cd backend
  uv run python scripts/test_graphiti_smoke.py
  ```

- Exercise one real end-to-end core case with your own source file and model
  credentials. Local automated tests cannot validate those external services.
- If this branch behaves correctly with real credentials, merge
  `feature/newInfo_0716` into `main`.

## Local verification before handoff

The branch was checked with the backend test suite, frontend source-contract
tests, production frontend build, Compose configuration validation, and Git
whitespace validation before it was pushed.
