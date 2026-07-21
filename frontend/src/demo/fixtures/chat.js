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
export const REPORT_CHAT_RESPONSE = `This report models how founders, partners, LPs, and frontier-lab researchers react if Y Combinator commits to an AGI-native selection and batch model — weighting agent leverage over headcount — versus keeping the classic batch playbook. Across ten simulated rounds on both platforms, sentiment moved from shock at a leaked "AGI-Native Track" memo, through a founder split (agent-native founders energized, traditional teams anxious, Velocity Program mocking YC's caution), through a genuine evidence clash — a telemetry study showing 3.2x more weekly releases versus a post-batch audit showing only 1.4x with 2.4x more critical incidents — and converged on cautious support once a bounded, reversible pilot structure was confirmed.

**Bottom line:** launch the staged AGI-Native Track for Winter 2027 — roughly 60 companies (about 15% of the batch), evaluated over two batch cycles, backed by $25M and six partners/program managers through 2027-06-30, with a pause trigger if incident rates exceed 1.5x baseline. Prioritize applicants with a supervision-weighted agent-leverage ratio of at least 10:1, demonstrated taste and judgment artifacts, distribution instinct, and fast learning speed — and screen out headcount-as-progress, demo-only agents, and founders with no owned distribution.

Ask me about a specific stakeholder, the scenario-analysis table, or the applicant-profile criteria if you'd like more detail.`

// Persona-flavored interview answers, keyed by agent_id (see AGENTS in
// actions.js — index-aligned with src/demo/fixtures/profiles.js — for the
// full cast). Deterministic per agent regardless of the exact prompt text,
// consistent with the rest of this scripted demo.
const POSITIONS = {
  0: "As the partner leading this proposal, I'm not choosing between 'AGI or not' — that decision already got made by founders themselves: 41% of our last batch ran agent fleets for the majority of engineering work. My job is designing the guardrails. I'm backing the staged AGI-Native Track: sixty companies, two batch cycles, a pause trigger at 1.5x baseline incidents, and an LP alignment check at cohort 1's exit. A full overhaul skips the part where we find out if the 3.2x number holds up under real oversight.",
  1: "My job is protecting what YC's name is worth, which means I don't sign off on anything without a way to reverse it. The staged track works for me because it has a written pause trigger and six named partners accountable for it — not because I'm confident agent-native teams outperform, but because I'm confident we'll know within two batch cycles instead of guessing.",
  2: "I left a frontier lab to help YC read the capability curve correctly, and the curve is still moving faster than most people's intuitions. The 3.2x-versus-1.4x fight isn't a contradiction — one is the ceiling agent leverage makes possible, the other is what teams actually capture without oversight. Selection has to test for the gap between those two numbers, not just cite whichever one supports a founder's pitch.",
  3: "I run Loomfield solo with a 40-agent fleet at $2.1M ARR, and I'll say the thing people skip: the fleet doesn't run itself. I review its output more hours than most nine-person teams spend writing code. If YC wants to fund founders like me without also funding the demo-only version of me, ask for the supervision-weighted leverage ratio, not the raw one.",
  4: "Parallel Desk is nine people, profitable, building normal B2B SaaS the normal way — and watching median team size drop to 1.8 people made me nervous before I understood the actual proposal. A bounded fifteen-percent pilot doesn't threaten teams like mine. An unbounded full overhaul might have. I can live with the version YC landed on.",
  5: "My team published the 3.2x telemetry number, and I stand behind it as a measured result for the first twelve weeks of agent-native teams. What I won't stand behind is treating it as the whole story — the post-batch audit's oversight-adjusted 1.4x is just as real, and any selection rubric has to account for both.",
  6: "AgentForge's own numbers are 15:1 raw agent leverage, 9:1 once you weight for supervision — and that gap is exactly why a raw ≥10:1 bar would misfire. I'd rather YC ask every applicant for their supervision-weighted ratio directly than trust whatever number sounds better in an application.",
  7: "I sit on an endowment committee, and anecdotes aren't a portfolio strategy — one founder's ARR doesn't tell me what a whole cohort will do. What changed my read was the structure: a bounded pilot, a pause trigger at 1.5x baseline incidents, and an LP alignment checkpoint at cohort 1's exit. That's a controlled experiment, not a bet, and I can underwrite that.",
  8: "Velocity runs an all-in AGI cohort already — no committee, no pilot theater, no two-batch waiting period. I think YC's staged approach is overly cautious, but I'll give them this: if their pause trigger and oversight-weighted rubric actually work, they'll have receipts we don't.",
  9: "I broke the story on YC's internal memo, and I've followed every twist since — the founder split, the LP concerns, the 3.2x-versus-1.4x fight. My read as a reporter: the staged track was the only option with real optionality. It can expand or reverse based on actual results; a full overhaul couldn't have been undone once announced.",
  10: "I build agent-eval tooling at Evalio, and my worry from day one was that 'agent-native' would become a checkbox instead of a practice. The post-batch audit's 2.4x incident number is exactly the kind of thing my tools are built to catch earlier. A rubric that only asks about fleet size, not eval discipline, is measuring the wrong thing.",
  11: "I work on alignment and safety, and the number I care about most is the 2.4x jump in critical incidents among agent-heavy teams without senior oversight. Selection criteria that don't test for oversight competence are optimizing for exactly the failure mode that number describes. The staged track, done right, is the first accelerator program I've seen build that test in from the start.",
  12: "I exited my last company in 2024 and I'm building agent-native now, mentoring first-time founders through this transition. The leverage is real, but leverage without taste just ships more mediocre things faster — that was true before agents and it's still true. The founders worth funding can tell you about a judgment call their fleet couldn't have made.",
  13: "As a Fortune-500 CIO, my procurement team already screens vendors on agent-leverage ratio before headcount — we buy outcomes, not org charts. Whatever YC decides about admissions, its founders need to be ready for that conversation on day one of a sales cycle, because enterprise buyers moved on this before any accelerator did.",
  14: "I'm an indie hacker, no accelerator, no fleet of forty agents — just me and whatever agents I can wire up myself. Consumer-facing, I don't think headcount or agent-leverage ratios matter as much as whether you actually shipped something people want. That said, I liked seeing 'distribution instinct' show up as a criterion — that's the one that actually predicts who survives.",
  15: "I track seed-stage market shifts for a living, and the compression from 3.1 to 1.8 median founders per team is the single biggest structural change I've seen this cycle. Whatever YC's internal debate looked like, the seed market already priced this in months ago — funds are already asking founders for their agent-leverage story before they ask about headcount."
}

export const interviewReply = agentId => {
  const agent = AGENTS[agentId]
  const position = POSITIONS[agentId]
  if (position) return position
  if (agent) return `As ${agent.role}, I'm following how YC's staged AGI-Native Track plays out against the alternative of a full batch-model overhaul.`
  return "I don't have a strong position to share on that."
}
