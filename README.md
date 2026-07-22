# WHAT IF WHAT IF — YC AGI Demo

This branch contains a presentation-only frontend demo for the Y Combinator AGI-era scenario. It is based on `sensei/Jun` and contains the UI and fixture changes made for the demo walkthrough.

## Branch

```text
deshi/Jung
```

## What changed

### Locked demo launcher

- Replaced the upload-first empty state with five locked evidence files:
  - `yc_agi_native_batch_blueprint_w27.pdf`
  - `frontier_lab_agent_economy_outlook_2027.pdf`
  - `agent_leverage_signals_w27.txt`
  - `tiny_team_selection_signals.md`
  - `lp_thesis_agi_native_accelerators.md`
- Locked the simulation prompt to the YC Winter 2027 AGI-native batch decision scenario.
- Set the displayed engine name to `whatIfDemo v.0.0.1`.
- Removed the Low Cost and Scalable marketing cards.
- Removed the model and reasoning configuration from the demo launcher.

### Graph Build and Environment Setup

- Standardized numbered workflow cards and their headers to pure white (`#FFFFFF`).
- Removed model and reasoning-effort controls from Environment Setup.
- Kept the existing backend defaults internally where needed.
- Made expanded persona and agent-configuration lists scroll inside their own blocks.
- Normalized spacing and backgrounds for agent, recommendation-algorithm, and LLM configuration blocks.
- Removed the experimental sticky section-header behavior.
- Corrected Step 05 so a prepared environment displays `Completed` instead of `In Progress`.
- Removed the Simulation Rounds Configuration interface.
- Locked Start Simulation to exactly 40 rounds.

### Simulation view

- Reduced the height and padding of the Info Plaza and Topic Community status cards.
- Placed each platform title and its metrics on one compact horizontal row.
- Preserved a stacked layout for narrow screens.

### Prediction report

- Added consistent white section surfaces from Coverage View onward.
- Added uniform internal padding, borders, rounded corners, and spacing between sections.
- Removed negative header margins that caused section backgrounds to run into the edges.
- Preserved the continuous bounded decision-refinement flow, including internal evidence handling and Information Value analysis.

### Responsive behavior

- Improved card and control reflow in narrow split-workbench layouts.
- Preserved page-level scrolling when graph and workbench panels stack.
- Kept large persona and agent lists bounded with independent scrolling.

## Run the demo

Run these commands from this branch's repository root:

```bash
cd frontend
npm install
npm run dev:demo
```

Open the local URL printed by Vite, normally:

```text
http://127.0.0.1:3000/
```

The equivalent explicit command is:

```bash
npm run dev -- --mode demo
```

## Demo mode versus normal development

`npm run dev:demo` loads `.env.demo`, which sets:

```text
VITE_DEMO_MODE=true
```

Demo mode enables the locked YC files, prompt, deterministic fixture responses, and full walkthrough without a live backend.

Plain `npm run dev` does not enable those fixtures. It starts the normal application, shows the editable upload state, and expects the backend at `http://localhost:5001`.

## Verification

Run the frontend tests:

```bash
cd frontend
npm run test:unit
```

Build the static demo:

```bash
npm run build:demo
```

The added regression coverage checks the locked launcher, white workflow surfaces, responsive graph/setup layouts, fixed 40-round launch, compact simulation status cards, and report-section spacing.

## Scope

- This is a deterministic demo website intended to show how the workflow runs.
- It does not require model API keys or an `.env` file beyond the included demo-mode configuration.
- The original working copy was not modified by this work.
