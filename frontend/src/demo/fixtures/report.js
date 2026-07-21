// Phase 4 (report generation) fixture: the report outline and section
// content for the Northstar Appliances scenario. Shared between
// src/demo/handlers/phase345.js (GET /api/report/:id) and
// src/demo/fixtures/agentLog.js (planning_complete.details.outline and each
// section_complete.details.content).
//
// Section content is limited-dialect Markdown (see src/utils/markdown.js):
// #-#### headings, lists, tables, blockquotes, http(s) links — no raw HTML
// or images, and no leading "## Title" line (the renderer strips it).

import { IDS } from './scenario.js'

export const OUTLINE = {
  title: 'Northstar Appliances — Restructuring Path Assessment',
  summary: 'Public and stakeholder reaction assessment for an immediate company-wide restructuring versus a staged, reversible pilot at Northstar Appliances.',
  sections: [
    { title: 'Executive Summary' },
    { title: 'Public Sentiment Timeline' },
    { title: 'Stakeholder Positions' },
    { title: 'Risk Scenarios' },
    { title: 'Pilot vs Full Restructuring Comparison' },
    { title: 'Recommendation' }
  ]
}

export const SECTIONS = {
  1: `Northstar Appliances faces roughly eleven weeks of liquidity runway, which is forcing a choice between an immediate, companywide restructuring and a staged, reversible pilot beginning at a single facility. Public and stakeholder reaction across both platforms consistently favored the staged option once its financial backstop became known.

Meridian Lending Group has offered to finance the pilot on the condition that Northstar reports liquidity weekly and protects supplier payments. That offer, combined with a UAW Local 1180 agreement that already requires consultation before any closures, gives the staged path a credible legal and financial foundation that an immediate restructuring would not have had.

Benchmark data suggested an 18% burn reduction over 90 days for staged programs, while Northstar's own supplier survey put the realistic number closer to 6%. Even at the more conservative estimate, stakeholders judged the staged pilot's optionality — the ability to expand or unwind based on real results — as worth more than the speed of an immediate restructuring.

**Recommendation preview:** proceed with the staged, reversible pilot under the Meridian financing terms, with weekly liquidity reporting and formal union consultation built in from day one. The full analysis and comparison follow in the sections below.`,

  2: `Sentiment moved through three distinct phases across the ten simulated rounds of social activity.

**Rounds 1-3 — Shock.** The initial announcement drew immediate concern from the Toledo and Macon plant managers, skepticism from a laid-off engineer who had seen similar announcements before, and pointed questions from an industry journalist about whether "staged pilot" secretly meant a single-site closure. CFO Marcus Lee's disclosure of the eleven-week liquidity runway anchored the rest of the conversation.

**Rounds 4-6 — Reaction.** UAW Local 1180 reasserted its consultation rights, the Toledo and Macon plant managers ran their own numbers against the 18% burn-reduction benchmark, and comments from a Meridian Lending Group analyst about backing a reversible pilot leaked into public conversation. Karlin Components' CFO pushed back on the 18% figure in favor of the supplier survey's more conservative 6% estimate.

**Rounds 7-10 — Settling.** Once Northstar confirmed the staged pilot structure, with weekly reporting to Meridian and consultation with the union, sentiment consolidated around cautious approval. Customers expressed relief that no plant closures had been announced, and the union reported its first on-schedule liquidity update within Meridian's target range by round 9.

By round 10, no meaningful stakeholder group was still advocating for an immediate, full restructuring.`,

  3: `- **Dana Whitfield, CEO** — prefers the staged pilot, conditioned on weekly liquidity reporting to Meridian.
- **Marcus Lee, CFO** — supports the pilot, frames it as time bought against the 11-week runway ceiling.
- **UAW Local 1180** — conditional support, contingent on consultation before any closures.
- **Meridian Lending Group** — willing to finance the pilot only, not a full restructuring, and only with weekly reporting and supplier payment protection.
- **Karlin Components** — supports the pilot, wants payment protection and earlier order visibility in exchange.
- **Toledo & Macon plant managers** — cautiously relieved, watching for a "temporary" pilot to quietly become permanent.

Interviews with Dana Whitfield, Denise Ruiz, and Tom Reyes (see the interview transcript above) converged on the same conclusion from three very different vantage points: the pilot only works if its guardrails — weekly reporting, consultation, and payment protection — are honored in practice, not just announced.

The most skeptical stakeholder voice belonged to the supplier side, where Tom Reyes argued for the more conservative 6% burn-reduction estimate over the 18% benchmark, warning that delayed approvals could cut it further still. That skepticism did not translate into opposition to the pilot itself, only into caution about oversized promises.`,

  4: `**Scenario A — Pilot underperforms its own targets.** If the pilot site misses its liquidity or burn-reduction targets, Meridian's financing terms allow the lender to pull support, which would force Northstar back toward the immediate restructuring option it was trying to avoid — but later and with less cash on hand.

**Scenario B — Consultation is treated as a formality.** Toledo and Macon plant managers raised the risk that leadership might satisfy the letter of the union agreement's consultation clause without meaningfully acting on the feedback. This is the scenario most likely to trigger a grievance and public backlash, based on the interview with Denise Ruiz.

**Scenario C — The pilot quietly becomes permanent.** A civic-advocacy comment on the timeline — "we've all seen a pilot quietly become permanent before" — reflects a real structural risk: without a defined evaluation date, a "temporary" pilot can drift into an unannounced full restructuring by default.

**Scenario D — Supplier confidence erodes if benchmarks are oversold.** Karlin Components' CFO pushed back on the 18% burn-reduction figure. If actual results land closer to his preferred 6% estimate and leadership had publicly leaned on 18%, that credibility gap could weaken supplier cooperation on future asks.

Of these, Scenario A carries the most immediate financial consequence, while Scenario C carries the most reputational risk with the workforce.`,

  5: `| Dimension | Staged, reversible pilot | Immediate full restructuring |
| --- | --- | --- |
| Liquidity impact | Financed by Meridian, conditional on weekly reporting | No external financing offered |
| Reversibility | Fully reversible if targets are missed | Effectively irreversible once executed |
| Union standing | Consistent with the consultation requirement | Very likely violates the consultation requirement |
| Supplier relationship | Karlin and other suppliers support it, with payment protection | Suppliers report no clarity or protection |
| Burn reduction (est.) | 6-18% over 90 days, a contested range | Faster, but unmeasured — no comparable benchmark cited |
| Public sentiment | Converged to cautious approval by round 10 | Never gained stakeholder support in the simulation |

The staged pilot outperforms the immediate restructuring option on every dimension stakeholders raised except speed. Even the burn-reduction estimates, which stakeholders actively disputed, only ranged from 6% to 18% — both numbers describe savings the immediate restructuring option cannot claim with comparable evidence, since no lender, union, or supplier data point supported it directly.

The only scenario in which immediate restructuring would outperform the pilot is one where speed alone is the dominant constraint — for example, if Northstar's liquidity window were closer to two or three weeks rather than eleven. That is not the situation described in this simulation.`,

  6: `**Proceed with the staged, reversible pilot**, beginning at a single facility, under the terms Meridian Lending Group has offered: weekly liquidity reporting and supplier payment protection.

1. Formalize weekly liquidity reporting to Meridian immediately, matching the cadence its analyst described as a condition of financing.
2. Open consultation with UAW Local 1180 before selecting the pilot site, satisfying the agreement's requirement in substance as well as form.
3. Set an explicit evaluation date and success threshold for the pilot so it cannot drift into a permanent state without a deliberate decision.
4. Communicate burn-reduction expectations conservatively, closer to the 6% supplier-survey estimate than the 18% benchmark, to preserve credibility with Karlin Components and other suppliers if results land in between.
5. Keep the immediate, full-restructuring option formally available as a fallback only if the pilot misses two consecutive weekly liquidity targets, but do not announce it as the default path.

This sequencing preserves optionality, keeps Meridian's financing available, satisfies the union agreement, and matches the sentiment that stakeholders converged on by the end of the simulation.`
}

const report = {
  report_id: IDS.reportId,
  simulation_id: IDS.simulationId,
  status: 'completed'
}

export default report
