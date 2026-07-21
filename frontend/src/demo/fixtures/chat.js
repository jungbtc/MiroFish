// Phase 5 (report chat / agent interview) fixture. Consumed by
// src/demo/handlers/phase345.js for POST /api/report/chat and
// POST /api/simulation/interview/batch.
//
// Both surfaces render their reply text through src/utils/markdown.js
// (see src/components/Step5Interaction.vue ~273, ~405), so replies use the
// same limited Markdown dialect as report sections.

import { AGENTS } from './actions.js'

// A single canned, keyword-independent answer for the Report Agent chat
// (POST /api/report/chat). The demo doesn't do real retrieval, so every
// question gets this grounded summary regardless of what was asked.
export const REPORT_CHAT_RESPONSE = `This report models public and stakeholder reaction to Northstar Appliances choosing between an immediate, companywide restructuring and a staged, reversible pilot. Across ten simulated rounds on both platforms, sentiment moved from initial shock at the liquidity disclosure, through union and supplier pushback on the competing burn-reduction benchmarks (18% industry vs. 6% supplier survey), and settled into cautious support once Meridian Lending Group's financing terms and the UAW Local 1180 consultation clause were confirmed.

**Bottom line:** proceed with the staged pilot at a single facility, backed by weekly liquidity reporting to Meridian and formal consultation with the union, keeping a full restructuring available only as a fallback if the pilot misses its own targets.

Ask me about a specific stakeholder, a risk scenario, or the burn-reduction numbers if you'd like more detail.`

// Persona-flavored interview answers, keyed by agent_id (see AGENTS in
// actions.js — index-aligned with src/demo/fixtures/profiles.js — for the
// full cast). Deterministic per agent regardless of the exact prompt text,
// consistent with the rest of this scripted demo.
const POSITIONS = {
  0: "As CEO, I'm weighing an immediate restructuring against a staged, reversible pilot. We disclosed our roughly 11-week liquidity runway because I'd rather our people understand the real constraint than guess at it. Right now I favor the staged pilot: Meridian Lending Group will back it if we report liquidity weekly and protect supplier payments, and UAW Local 1180 gets the consultation our agreement requires. I'd only move to a full restructuring if the pilot missed its own targets.",
  1: "As CFO, the number that drives this decision is our liquidity runway — about 11 weeks at current burn. A staged pilot buys us time to test whether the 18% burn-reduction benchmark holds here, without burning the goodwill an immediate, companywide restructuring would cost us with the union and our suppliers.",
  2: "I manage the Toledo Assembly Plant. Morale has been eroding after two rounds of layoff rumors already this year, so what matters most to me is whether leadership actually consults us before any closure, not just whether the numbers look good on a slide. I'd rather see a pilot than an abrupt shutdown.",
  3: "I manage the Macon Assembly Plant. A phased approach is the only version of this that doesn't cost us our most skilled line workers to competitors overnight. Our own numbers land closer to 10-12% burn reduction — between the 18% benchmark and the 6% supplier-survey floor — and a pilot is what lets us prove that before anything irreversible happens.",
  4: "I manage external messaging for Northstar. My job through this has been making sure employees, retail partners, and press get consistent, timely information instead of guessing from rumors — that's as true for the restructuring announcement as for the pilot confirmation that followed it.",
  5: "I run supply chain for Northstar. I'm coordinating directly with Karlin Components and our other suppliers to protect critical payment terms under the pilot, since that's the piece that determines whether our suppliers stay cooperative through this.",
  6: "As Chief Shop Steward for UAW Local 1180, our position was never complicated: any pilot needs a firm sunset date, and full consultation rights before any permanent closure. That's now in writing, and we'll keep tracking the weekly liquidity reports as closely as Meridian does.",
  7: "I was laid off from the Toledo plant in a prior cost round, and the thing I still hold against that process is how unclear the communication was. Seeing consultation actually enforced this time, instead of skipped, is the biggest difference — and the reason I think the staged pilot is the right call here.",
  8: "As Karlin Components' CFO, I'd put more weight on our own 6% burn-reduction estimate than the 18% benchmark leadership cited; delayed approvals and unclear ownership are exactly what could cut that number down further. We can commit to weekly reporting on our end to help the pilot succeed instead of absorbing a sudden full stop.",
  9: "As Meridian's senior credit analyst, I drafted the covenant terms tying continued credit access to weekly liquidity reporting and critical-supplier payment protection. A reversible pilot with those conditions is a fundamentally different risk than an unstructured full restructuring — that structure is what makes financing comfortable for us.",
  10: "I handle merchandising for HomePlex. Before committing to next season's purchase orders, I need a written supply-continuity plan from Northstar — a pilot with real reporting is much easier to plan shelf space around than an abrupt full restructuring would have been.",
  11: "I cover this story as an industry journalist, including the supplier survey findings on cash-burn impact. My read is that the staged pilot was the only option with real optionality — it could expand or unwind based on actual results, while an immediate restructuring couldn't have been undone once announced.",
  12: "I moderate the Northstar Loyalists community — about 40,000 members. What I'm tracking most closely are the warranty and service-continuity questions flooding in from long-time customers; they want a straight answer, not corporate language.",
  13: "I speak for budget-conscious, price-sensitive households. My worry through all of this has been simple: whatever this restructuring costs, please don't pass all of it onto appliance prices. I'm relieved this didn't turn into a headline about plants closing overnight.",
  14: "I'm active in the Appliance Repair Community Forum, tracking parts-supply risk tied to this decision. Selfishly, I just want parts availability to keep working no matter which path Northstar takes internally.",
  15: "I organize civic support for Toledo Assembly Plant workers ahead of any closure announcement. Cautiously relieved is the honest way to describe where we are — we've seen a \"temporary\" pilot quietly become permanent before, so we're not declaring victory yet."
}

export const interviewReply = agentId => {
  const agent = AGENTS[agentId]
  const position = POSITIONS[agentId]
  if (position) return position
  if (agent) return `As ${agent.role}, I'm following how Northstar's staged pilot plays out against the alternative of an immediate restructuring.`
  return "I don't have a strong position to share on that."
}
