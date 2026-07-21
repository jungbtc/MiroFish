// Phase 4 (report generation) fixture: the report outline and section
// content for the "Y Combinator in the AGI era" scenario. Shared between
// src/demo/handlers/phase345.js (GET /api/report/:id) and
// src/demo/fixtures/agentLog.js (planning_complete.details.outline and each
// section_complete.details.content).
//
// Section content is limited-dialect Markdown (see src/utils/markdown.js):
// #-#### headings, lists, tables, blockquotes, http(s) links — no raw HTML
// or images, and no leading "## Title" line (the renderer strips it).

import { IDS } from './scenario.js'

export const OUTLINE = {
  title: 'Y Combinator in the AGI Transition — Batch Strategy Coverage Initiation',
  summary: 'Equity-research-style coverage of how Y Combinator should prepare for the AGI era: full batch-model overhaul vs. a staged, reversible AGI-Native Track vs. the classic playbook, and which applicant profile YC should prioritize for Winter 2027.',
  sections: [
    { title: 'Coverage View: Y Combinator in the AGI Transition' },
    { title: 'What the Simulation Surfaced: Discourse & Sentiment Arc' },
    { title: 'Stakeholder Book' },
    { title: 'Scenario Analysis' },
    { title: 'The AGI-Era Applicant Profile' },
    { title: 'Recommendation & 12-Month Roadmap' }
  ]
}

export const SECTIONS = {
  1: `**Rating: OVERWEIGHT — Staged AGI-Native Track** (conviction 8.2/10)

Y Combinator sits at an inflection point most accelerators haven't priced in yet. 41% of the most recent batch used agent fleets for the majority of engineering work, up from just 9% two batches earlier, and median founding-team size has compressed to 1.8 people, down from 3.1 in 2023. The question is no longer whether agent leverage changes who YC should fund — it already has — but how fast YC's admissions rubric and batch curriculum should move to match it.

**Key stats:**
- 41% of the latest batch is agent-native by engineering effort, vs. 9% two batches ago.
- Median founding-team size: 1.8 people, down from 3.1 in 2023.
- Telemetry study: 3.2× more weekly releases for agent-native teams in their first 12 weeks. Post-batch audit: only 1.4× once senior oversight and ownership are controlled for, with 2.4× more critical production incidents where oversight was missing.

Two datasets frame the debate and disagree with each other by design. Neither number, taken alone, tells YC what to do — the 3.2× figure is a ceiling agent leverage makes possible, and the 1.4× figure is what teams without oversight competence actually capture, at a real cost in incidents.

**Recommendation preview:** commit to a bounded, reversible AGI-Native Track — roughly 60 companies, about 15% of the Winter 2027 batch — rather than a full batch-model overhaul or a defensive status quo. The pilot runs two full batch cycles before any wider commitment, backed by $25M and six dedicated partners/program managers through 2027-06-30, with a hard pause trigger if incident rates exceed 1.5× baseline. The full analysis and comparison follow in the sections below.`,

  2: `Sentiment moved through five distinct phases across the ten simulated rounds of social activity.

**Rounds 1-2 — The leak.** The Batch Report broke news of an internal "AGI-Native Track" memo before YC said anything on the record. #AGInativeYC trended within hours. Managing Partner Marcus Oyelaran's initial response — measured, non-committal — did little to slow the hot-take cycle once Group Partner Elena Voss confirmed the 41%-of-batch figure was real.

**Rounds 3-4 — The founder split.** Kai Nakamura's public confirmation that he runs Loomfield solo on a 40-agent fleet at $2.1M ARR became the cycle's defining data point, celebrated by agent-native founders and unsettling to traditional teams like Sofia Marek's nine-person Parallel Desk. Velocity Program's Dev Kapoor used the moment to needle YC publicly for running a two-batch study on something his rival program had "already decided."

**Rounds 5-6 — LP and enterprise signal.** Rachel Adeyemi surfaced institutional-investor unease — an anecdote isn't a portfolio strategy — while Priya Shenoy's capability-curve data and Hana Sato's on-record confirmation that her Fortune-500 procurement team now screens vendors on agent-leverage ratio before headcount gave the pro-track side its strongest non-founder evidence yet.

**Rounds 7-8 — The evidence clash.** Dr. Wen Zhao's 3.2× telemetry study landed first and spread fast. Aisha Rahman's post-batch audit citing 1.4× and 2.4× more incidents followed within a day, reframing the conversation from "how much faster" to "faster at what cost." Kai Nakamura's admission that he reviews agent output more hours than most nine-person teams spend writing code became the pivot point the discourse needed.

**Rounds 9-10 — Convergence.** Once Elena Voss confirmed the staged, 60-company, two-cycle pilot structure with a written pause trigger, opposition softened on every side. By round 10, no stakeholder group — not the skeptical LP, not the anxious traditional founder, not the safety researcher — was still arguing for either the full overhaul or the status quo.`,

  3: `- **Elena Voss, Group Partner (AGI-Native Track lead)** — champions the staged pilot as the only structure her committee can defend to LPs and skeptical partners alike.

  > "A bounded pilot with a real evaluation window is a different risk than a blanket policy change."

- **Marcus Oyelaran, Managing Partner** — protects the brand; will not sign off without a written pause trigger and named owners.

  > "Six partners staffed and a pause trigger written down before a single company is admitted — that's the guardrail I was asking for."

- **Priya Shenoy, Visiting Partner (ex-frontier lab)** — frames the debate as capability-curve literacy, not ideology.

  > "3.2× raw velocity is the ceiling agent leverage makes possible; 1.4× is what teams without oversight competence actually capture."

- **Kai Nakamura, Founder, Loomfield** — the agent-native archetype; his candor about supervision hours reframes the whole debate.

  > "I spend more hours reviewing agent output than most nine-person teams spend writing code."

- **Sofia Marek, Co-Founder, Parallel Desk** — the traditional-team counterweight; profitable, anxious, ultimately reassured by the bounded pilot size.

  > "We're profitable. We're just not a good story right now."

- **Rachel Adeyemi, LP, University Endowment** — institutional skepticism that shapes the guardrails more than it blocks the pilot.

  > "Anecdotes aren't a portfolio strategy."

- **Dev Kapoor, Partner, Velocity Program** — the rival's caution-mocking foil; a useful contrast case for what YC deliberately isn't doing.

  > "YC is running a two-batch study to decide something we decided a year ago."

- **Dr. Wen Zhao (Helios Research) and Aisha Rahman (Alignment & Safety)** — supply the evidence conflict at the center of the thesis: 3.2× vs. 1.4×, and the 2.4× incident gap that makes oversight the real variable.

- **Hana Sato, CIO** — the demand-side proof point: enterprise procurement already screens on agent-leverage ratio, ahead of any accelerator's policy change.

Interviews conducted with Elena Voss, Rachel Adeyemi, and Kai Nakamura converge on one point despite very different vantage points: the pilot only works if its guardrails — the pause trigger, the oversight-weighted leverage bar, and the two-cycle evaluation window — are enforced in practice, not just announced in a memo.`,

  4: `| Dimension | Full Overhaul | Staged AGI-Native Track | Status Quo |
| --- | --- | --- | --- |
| Deal-flow quality | Highest ceiling, unproven floor — admits both Kai-caliber founders and demo-only fleets indiscriminately | Best risk-adjusted quality — a 60-company pilot lets the interview rubric select for supervision competence before scaling | Deal flow erodes as agent-native founders self-select into Velocity Program and peers |
| Brand risk | Highest — a public incident in an unvetted full-scale cohort is a YC-wide story | Contained — a bad cohort is 15% of one batch, with a pre-committed pause trigger | Low near-term, high long-term — "YC missed AGI" becomes the story instead |
| LP confidence | Lowest — Rachel Adeyemi's committee explicitly will not underwrite an unbounded policy shift | Highest achievable — bounded size, fixed evaluation window, and named owners satisfy the "anecdotes aren't a strategy" objection | Erodes gradually as returns lag agent-native peer accelerators |
| Expected batch outcome | 3.2× velocity ceiling, but 2.4× incident rate if oversight isn't selected for | 1.4×-3.2× range depending on execution, with incident rate capped by the pause trigger | Flat — batch performance tracks the shrinking pool of traditional-team applicants |
| Reversibility | Effectively irreversible once the whole batch model changes | Fully reversible — pauses at >1.5× baseline incident rate, sunsets at cohort-1 exit if the LP alignment check fails | Reversible in theory, but reversing under competitive pressure gets harder every batch |

The staged track dominates on every dimension except raw velocity ceiling, and even there it captures the bulk of the upside — 1.4× is still a real edge — while capping the tail risk the post-batch audit already quantified at 2.4×. The status quo's apparent safety is an illusion once procurement behavior (Hana Sato) and founder team-size trends (1.8 vs. 3.1) are taken as given rather than hypothetical.`,

  5: `The evidence across all sixteen simulated stakeholders converges on four selection criteria YC should weight explicitly, replacing headcount and demo polish as proxies for founder quality:

1. **Agent-leverage ratio ≥10:1, supervision-weighted.** Not the raw ratio — Tomas Lindqvist's distinction between AgentForge's 15:1 raw ratio and 9:1 supervision-weighted ratio is the whole ballgame. A rubric that uses the raw number admits exactly the unsupervised risk the post-batch audit flagged at 2.4×.
2. **Demonstrated taste and judgment artifacts.** Kai Nakamura's candor about reviewing agent output more than most nine-person teams write code is the tell: agent-native founders worth funding can point to specific judgment calls their fleet couldn't have made alone.
3. **Distribution instinct.** Leverage produces output; it doesn't produce customers. The applicant profile should reward founders who can show owned distribution, not just fast shipping.
4. **Learning speed.** With teams this small, the founder is the only feedback loop. Partner interviews should probe how fast a founder updates a wrong call, not just how fast their fleet ships the next one.

**Anti-patterns to screen out:** headcount-as-progress (hiring to look serious rather than to solve a real bottleneck); demo-only agents (fleets that produce impressive walkthroughs but no production ownership); and no owned distribution (agent leverage spent entirely on building, none on reaching customers).

Partner interviews change materially under this rubric: instead of asking "how many engineers," interviewers ask for the supervision-weighted leverage ratio directly, request one specific example of the founder overriding or correcting agent output, and probe distribution channels before touching the product demo at all.`,

  6: `**Recommendation: launch the staged AGI-Native Track for the Winter 2027 batch.** Applications open September 2026; go/no-go on the wider rollout is due by 2026-08-15, ahead of that application window.

1. **Cohort 1 (Winter 2027).** Admit up to 60 companies (~15% of batch) to the AGI-Native Track under the supervision-weighted ≥10:1 leverage bar, staffed by 6 partners/program managers, funded by a $25M binding allocation through 2027-06-30.
2. **Weekly telemetry, not batch-end telemetry.** Track release velocity and incident rate weekly per company, not just at demo day, so the 3.2×-vs-1.4× question gets resolved with this cohort's own data instead of re-litigated with someone else's.
3. **Pause trigger.** If incident rate across the pilot cohort exceeds 1.5× baseline at any point, pause new admissions to the track immediately pending review — the guardrail Marcus Oyelaran required before signing off.
4. **LP alignment checkpoint.** At cohort 1's exit (roughly two batch cycles out), review results directly with LP committees, addressing Rachel Adeyemi's objection with cohort-level outcomes instead of a single founder's anecdote.
5. **KPIs for the go/no-go call:** weekly release multiple versus traditional-track peers, incident rate versus the 1.5× pause threshold, cohort-1 follow-on funding rate, and LP renewal sentiment at the alignment checkpoint.
6. **If the pilot clears its bar:** expand the AGI-Native Track's share of the batch for Summer 2027. **If it doesn't:** revert admissions to the classic playbook for the affected slice, preserving everything learned about the supervision-weighted rubric for future batches.

This sequencing captures the upside Priya Shenoy's capability curves and Hana Sato's procurement data both point to, without underwriting the downside the 2.4× incident figure already quantified — and it gives YC a real answer, backed by its own data, before the Winter 2027 application window opens.`
}

const report = {
  report_id: IDS.reportId,
  simulation_id: IDS.simulationId,
  status: 'completed'
}

export default report
