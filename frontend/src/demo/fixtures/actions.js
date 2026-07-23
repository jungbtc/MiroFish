// Phase 3 (simulation run) fixture: the 16-agent cast for the "Y Combinator
// in the AGI era" scenario and the ~80 scripted social actions they take
// across 10 simulated rounds (both platforms). Consumed by
// src/demo/handlers/phase345.js to derive /run-status, /run-status/detail,
// and by src/demo/fixtures/chat.js for interview personas.
//
// Narrative arc (see .context/yc-scenario-bible.md):
//   Rounds 1-2  — The Batch Report leaks "YC drafting an AGI-Native Track"
//   Rounds 3-4  — founder split: agent-native founders celebrate, traditional
//                 teams grow anxious, Velocity Program mocks YC's caution
//   Rounds 5-6  — LP concern thread, capability-curve data, enterprise
//                 procurement already assumes agent-native teams
//   Rounds 7-8  — telemetry study (3.2x) vs. post-batch audit (1.4x, 2.4x
//                 incidents) clash publicly — the evidence conflict
//   Rounds 9-10 — consensus converges on the staged, reversible track with
//                 oversight guardrails
//
// IMPORTANT: this cast (id/name/username) is index-aligned with
// src/demo/fixtures/profiles.js (the phase12 fixture Step2EnvSetup.vue and
// Step5Interaction.vue's agent picker read from). Keep the two in sync —
// `name` here mirrors profiles.js's `username` field (display name) and
// `username` here mirrors profiles.js's `name` field (handle/slug), so a
// persona picked in Step5 by agent_id matches the voice used in the Step3
// timeline and the Step4/5 interview replies.

import { ts } from './scenario.js'

export const AGENTS = [
  { id: 0, name: 'Elena Voss', username: 'elena_voss_ycagi', role: 'Group Partner, AGI-Native Track Lead, Y Combinator' },
  { id: 1, name: 'Marcus Oyelaran', username: 'marcus_oyelaran_yc', role: 'Managing Partner, Y Combinator' },
  { id: 2, name: 'Priya Shenoy', username: 'priya_shenoy_yc', role: 'Visiting Partner, Y Combinator (ex-Frontier Lab)' },
  { id: 3, name: 'Kai Nakamura', username: 'kai_loomfield', role: 'Solo Founder, Loomfield' },
  { id: 4, name: 'Sofia Marek', username: 'sofia_paralleldesk', role: 'Co-Founder, Parallel Desk' },
  { id: 5, name: 'Dr. Wen Zhao', username: 'wen_zhao_helios', role: 'Research Scientist, Helios Research' },
  { id: 6, name: 'Tomas Lindqvist', username: 'tomas_agentforge', role: 'CTO, AgentForge' },
  { id: 7, name: 'Rachel Adeyemi', username: 'rachel_adeyemi_lp', role: 'LP, University Endowment' },
  { id: 8, name: 'Dev Kapoor', username: 'dev_kapoor_velocity', role: 'Partner, Velocity Program' },
  { id: 9, name: 'Maya Chen', username: 'maya_chen_batchreport', role: 'Journalist, The Batch Report' },
  { id: 10, name: 'Jonah Price', username: 'jonah_price_evalio', role: 'Founder, Evalio' },
  { id: 11, name: 'Aisha Rahman', username: 'aisha_rahman_safety', role: 'Alignment & Safety Researcher' },
  { id: 12, name: 'Leo Martins', username: 'leo_martins_founder', role: 'Second-Time Founder (Agent-Native)' },
  { id: 13, name: 'Hana Sato', username: 'hana_sato_cio', role: 'CIO, Fortune-500 Retail Group' },
  { id: 14, name: 'Gabe Torres', username: 'gabe_torres_indie', role: 'Indie Hacker, Consumer Agent Apps' },
  { id: 15, name: 'Nadia Petrova', username: 'nadia_petrova_vc', role: 'Early-Stage VC Analyst' }
]

const byId = id => AGENTS[id]

// Each row: [agentId, platform, action_type, action_args]. Rounds are
// implicit — every 8 rows completes a round (4 twitter + 4 reddit).
// Twitter carries the partner/institutional/media voices; Reddit carries
// the founder and researcher grassroots discourse — mirroring
// profiles.js's entity_type groupings (Partner/InvestorLP/MediaOutlet/
// AcceleratorProgram/Enterprise buyer vs. Founder/ResearchLab).
const RAW = [
  // Round 1 — the leak
  [9, 'twitter', 'CREATE_POST', {
    content: "SCOOP: Y Combinator is quietly drafting an 'AGI-Native Track' — a parallel admissions lane for founders running agent fleets instead of hiring. Internal memo obtained by The Batch Report describes weighting agent leverage over headcount for the first time in YC's history. #AGInativeYC"
  }],
  [1, 'twitter', 'CREATE_COMMENT', {
    content: "We're evaluating several approaches to how AGI changes company-building. No final decision has been made on batch structure, admissions criteria, or timing. We'll say more when there's something to say.",
    post_id: 'post_4001',
    post_author_name: 'Maya Chen',
    post_content: "SCOOP: Y Combinator is quietly drafting an 'AGI-Native Track' — a parallel admissions lane for founders running agent fleets instead of hiring."
  }],
  [0, 'twitter', 'CREATE_POST', {
    content: "The memo Maya's story references is real, in the sense that we draft a lot of memos. What's also real: 41% of our most recent batch used agent fleets for the majority of engineering work, up from 9% two batches ago. Whatever we do next has to start from that fact."
  }],
  [8, 'twitter', 'LIKE_POST', {
    post_author_name: 'Maya Chen',
    post_content: "SCOOP: Y Combinator is quietly drafting an 'AGI-Native Track' — a parallel admissions lane for founders running agent fleets instead of hiring."
  }],
  [4, 'reddit', 'CREATE_POST', {
    content: "Reading The Batch Report piece with my stomach in a knot. We're 9 people building B2B SaaS the normal way. If YC starts admitting teams of 1.8 founders with forty agents each, where does that leave the rest of us in the room?"
  }],
  [6, 'reddit', 'CREATE_COMMENT', {
    content: "Genuinely don't get the anxiety. We build the orchestration layer these fleets run on — demand for teams like Sofia's isn't going anywhere, it's the mix of who gets admitted that's shifting, not the market for good software.",
    post_id: 'post_4002',
    post_author_name: 'Sofia Marek',
    post_content: "Reading The Batch Report piece with my stomach in a knot. We're 9 people building B2B SaaS the normal way."
  }],
  [12, 'reddit', 'CREATE_POST', {
    content: 'Mentoring three first-time founders through this news cycle today. My advice hasn\'t changed: the leverage is real, but leverage without taste just ships more mediocre things faster. That part of the game was never going to change.'
  }],
  [14, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Leo Martins',
    post_content: "Mentoring three first-time founders through this news cycle today. My advice hasn't changed: the leverage is real, but leverage without taste just ships more mediocre things faster."
  }],

  // Round 2 — #AGInativeYC trends, the numbers get sharper
  [0, 'twitter', 'CREATE_POST', {
    content: "To be clear about what's driving this: median founding-team size in our latest batch is 1.8 people, down from 3.1 in 2023. That's not a policy choice, it's what founders are already doing. #AGInativeYC is a real trend, not a marketing line."
  }],
  [9, 'twitter', 'QUOTE_POST', {
    quote_content: '1.8 vs 3.1 is the chart of the year, honestly. Publishing the full memo excerpt in tomorrow\'s Batch Report.',
    original_content: 'median founding-team size in our latest batch is 1.8 people, down from 3.1 in 2023.',
    original_author_name: 'Elena Voss'
  }],
  [15, 'twitter', 'SEARCH_POSTS', { query: 'YC AGI-Native Track leaked memo' }],
  [7, 'twitter', 'CREATE_COMMENT', {
    content: "1.8 founders running a batch company is a staffing story, not just a technology story. Before anyone celebrates, someone should ask who's actually accountable when something breaks.",
    post_id: 'post_4004',
    post_author_name: 'Elena Voss',
    post_content: 'median founding-team size in our latest batch is 1.8 people, down from 3.1 in 2023.'
  }],
  [10, 'reddit', 'CREATE_POST', {
    content: "Building Evalio (agent eval tooling) and I'll say the quiet part: half the 'AGI-native' founders I know can't tell you why their agent fleet's output is good, just that it's fast. Fast and good are not the same axis."
  }],
  [11, 'reddit', 'CREATE_COMMENT', {
    content: "This is the risk nobody in the hot-take cycle wants to name. Speed without oversight is exactly how you get incidents, not just mediocre demos.",
    post_id: 'post_4005',
    post_author_name: 'Jonah Price',
    post_content: "Building Evalio (agent eval tooling) and I'll say the quiet part: half the 'AGI-native' founders I know can't tell you why their agent fleet's output is good, just that it's fast."
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: "AgentForge's dashboards are getting slammed with new signups since the leak — mostly first-time founders trying to wire up an agent fleet in a weekend to look admissible. That is exactly the wrong lesson to take from this."
  }],
  [4, 'reddit', 'CREATE_COMMENT', {
    content: "Comforting to hear I'm not the only one worried about that. If 'agent fleet' becomes a checkbox instead of an actual practice, YC is going to admit a lot of theater.",
    post_id: 'post_4006',
    post_author_name: 'Tomas Lindqvist',
    post_content: "AgentForge's dashboards are getting slammed with new signups since the leak — mostly first-time founders trying to wire up an agent fleet in a weekend to look admissible."
  }],

  // Round 3 — founder split begins
  [3, 'twitter', 'CREATE_POST', {
    content: "Can confirm the leak is directionally right, and honestly overdue. I run Loomfield solo with a 40-agent fleet at $2.1M ARR. I didn't get here because someone gave me nine cofounders — I got here because the fleet does the work three of me couldn't."
  }],
  [1, 'twitter', 'CREATE_COMMENT', {
    content: "Kai's numbers are exactly the kind of data point we're weighing seriously. One founder is not a policy though — we need to see it hold across sixty companies before we bet the batch on it.",
    post_id: 'post_4007',
    post_author_name: 'Kai Nakamura',
    post_content: "Can confirm the leak is directionally right, and honestly overdue. I run Loomfield solo with a 40-agent fleet at $2.1M ARR."
  }],
  [8, 'twitter', 'QUOTE_POST', {
    quote_content: "'We need to see it hold' is the most YC sentence ever written. We already run an all-in AGI track at Velocity — no committee, no pilot theater. Kai would've been admitted to us in a week.",
    original_content: 'One founder is not a policy though — we need to see it hold across sixty companies before we bet the batch on it.',
    original_author_name: 'Marcus Oyelaran'
  }],
  [13, 'twitter', 'LIKE_POST', {
    post_author_name: 'Kai Nakamura',
    post_content: "Can confirm the leak is directionally right, and honestly overdue. I run Loomfield solo with a 40-agent fleet at $2.1M ARR."
  }],
  [4, 'reddit', 'CREATE_POST', {
    content: "Watching Kai's tweet get 40,000 likes while our team of 9 grinds through a normal enterprise sales cycle is a specific kind of demoralizing. We're profitable. We're just not a good story right now."
  }],
  [12, 'reddit', 'CREATE_COMMENT', {
    content: "Sofia, profitable and boring is still a great position. I exited in 2024 with a normal team and I'm rebuilding agent-native now — the skills transfer, the story doesn't have to be the same to end well.",
    post_id: 'post_4008',
    post_author_name: 'Sofia Marek',
    post_content: "Watching Kai's tweet get 40,000 likes while our team of 9 grinds through a normal enterprise sales cycle is a specific kind of demoralizing."
  }],
  [14, 'reddit', 'CREATE_POST', {
    content: "Velocity Program's 'no committee, no pilot theater' line is doing a lot of marketing work for a program that hasn't published a single retention number. Somebody ask Dev Kapoor for his cohort's 12-month survival rate."
  }],
  [6, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Gabe Torres',
    post_content: "Velocity Program's 'no committee, no pilot theater' line is doing a lot of marketing work for a program that hasn't published a single retention number."
  }],

  // Round 4 — Velocity Program mocks YC's caution
  [8, 'twitter', 'CREATE_POST', {
    content: "Since people are asking: Velocity's all-in AGI cohort has no headcount minimums, no 'oversight competence' interview, and no eighteen-month pilot before we commit. YC is running a two-batch study to decide something we decided a year ago."
  }],
  [2, 'twitter', 'CREATE_COMMENT', {
    content: "Priya here — I left a frontier lab to do this job, and 'decided a year ago' undersells how fast the capability curve is still moving. Moving fast on an outdated read of the curve isn't the same as moving fast.",
    post_id: 'post_4010',
    post_author_name: 'Dev Kapoor',
    post_content: "Velocity's all-in AGI cohort has no headcount minimums, no 'oversight competence' interview, and no eighteen-month pilot before we commit."
  }],
  [15, 'twitter', 'SEARCH_POSTS', { query: 'Velocity Program AGI cohort retention rate' }],
  [7, 'twitter', 'LIKE_POST', {
    post_author_name: 'Priya Shenoy',
    post_content: "I left a frontier lab to do this job, and 'decided a year ago' undersells how fast the capability curve is still moving."
  }],
  [10, 'reddit', 'CREATE_POST', {
    content: "Genuine question from the evals side: has anyone at Velocity published incident rates for their agent-heavy cohort? Everyone's citing release velocity. Nobody's citing what breaks in production."
  }],
  [11, 'reddit', 'CREATE_COMMENT', {
    content: "No, and I'd bet money that's not an accident. Release velocity is the easy number to brag about. Incident rate is the number that tells you whether anyone senior is actually watching.",
    post_id: 'post_4011',
    post_author_name: 'Jonah Price',
    post_content: "Genuine question from the evals side: has anyone at Velocity published incident rates for their agent-heavy cohort?"
  }],
  [6, 'reddit', 'FOLLOW', { target_user: 'jonah_price_evalio' }],
  [14, 'reddit', 'DOWNVOTE_POST', {
    post_content: 'just admit every solo founder with an API key already, headcount is a vanity metric, cope harder traditional teams'
  }],

  // Round 5 — LP concern, capability curves
  [7, 'twitter', 'CREATE_POST', {
    content: "Speaking for myself, not the endowment: our committee is nervous about an 'AGI-Native Track' before YC can show accelerator-level returns hold up under it. A 40-agent solo founder is a great anecdote. Anecdotes aren't a portfolio strategy."
  }],
  [0, 'twitter', 'CREATE_COMMENT', {
    content: "Fair pushback, Rachel. That's exactly why we're not proposing a full overhaul — we're scoping a pilot small enough to fail safely and large enough to actually tell us something.",
    post_id: 'post_4012',
    post_author_name: 'Rachel Adeyemi',
    post_content: "our committee is nervous about an 'AGI-Native Track' before YC can show accelerator-level returns hold up under it."
  }],
  [2, 'twitter', 'CREATE_POST', {
    content: "Posting the capability curve slide LPs keep asking me for. The gap between what frontier models could do a year ago and what they can do unsupervised today is the entire reason this conversation exists — it's not hype, it's a chart."
  }],
  [9, 'twitter', 'QUOTE_POST', {
    quote_content: 'Getting this slide from three different sources today. Running the full chart in tomorrow\'s Batch Report alongside Rachel\'s LP concerns.',
    original_content: 'Posting the capability curve slide LPs keep asking me for.',
    original_author_name: 'Priya Shenoy'
  }],
  [4, 'reddit', 'CREATE_POST', {
    content: "Enterprise buyers are already ahead of this conversation, for what it's worth. Our biggest customer's procurement team told us flat out this quarter: 'we're buying outcomes now, we stopped asking about headcount.' That's not a YC policy, that's already the market."
  }],
  [6, 'reddit', 'CREATE_COMMENT', {
    content: "This matches what I'm hearing from AgentForge customers too. Procurement asking for agent-leverage ratios in RFPs was not on my 2026 bingo card, but here we are.",
    post_id: 'post_4013',
    post_author_name: 'Sofia Marek',
    post_content: "Our biggest customer's procurement team told us flat out this quarter: 'we're buying outcomes now, we stopped asking about headcount.'"
  }],
  [12, 'reddit', 'CREATE_POST', {
    content: "If procurement has already moved, the debate about whether YC 'should' change is a little late. The real question is whether the selection rubric can measure judgment and not just fleet size. That's the harder problem."
  }],
  [10, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Leo Martins',
    post_content: "If procurement has already moved, the debate about whether YC 'should' change is a little late. The real question is whether the selection rubric can measure judgment and not just fleet size."
  }],

  // Round 6 — enterprise buyer confirms, agent-leverage ratio definitions surface
  [13, 'twitter', 'CREATE_POST', {
    content: "Confirming what's being quoted secondhand: as CIO, my procurement team now asks vendors for their agent-leverage ratio before headcount. We buy outcomes, not org charts. Any accelerator not preparing founders for that conversation is preparing them for the wrong decade."
  }],
  [1, 'twitter', 'CREATE_COMMENT', {
    content: "This is the strongest single data point in this whole thread. If enterprise buyers are already scoring vendors this way, admissions criteria that ignore it are actively mis-preparing founders.",
    post_id: 'post_4015',
    post_author_name: 'Hana Sato',
    post_content: "as CIO, my procurement team now asks vendors for their agent-leverage ratio before headcount. We buy outcomes, not org charts."
  }],
  [9, 'twitter', 'LIKE_POST', {
    post_author_name: 'Hana Sato',
    post_content: "as CIO, my procurement team now asks vendors for their agent-leverage ratio before headcount. We buy outcomes, not org charts."
  }],
  [15, 'twitter', 'SEARCH_POSTS', { query: 'enterprise procurement agent leverage ratio vendors' }],
  [6, 'reddit', 'CREATE_POST', {
    content: "Since people keep asking for specifics: AgentForge's own agent-leverage ratio is roughly 15:1 raw, but the number that should actually matter to a selection committee is closer to 9:1 once you weight for the agents that need real human review versus the ones that don't."
  }],
  [11, 'reddit', 'CREATE_COMMENT', {
    content: "That distinction — raw ratio versus supervision-weighted ratio — is the whole ballgame and almost nobody's making it publicly. A ≥10:1 bar that uses the raw number will admit a lot of unsupervised risk.",
    post_id: 'post_4016',
    post_author_name: 'Tomas Lindqvist',
    post_content: "AgentForge's own agent-leverage ratio is roughly 15:1 raw, but the number that should actually matter to a selection committee is closer to 9:1 once you weight for supervision."
  }],
  [12, 'reddit', 'CREATE_POST', {
    content: "Seconding Tomas and Aisha both. I've mentored three agent-native founders this batch and the ones worth funding all talk about their supervision ratio unprompted. The ones who don't mention it are the ones you should worry about."
  }],
  [14, 'reddit', 'FOLLOW', { target_user: 'aisha_rahman_safety' }],

  // Round 7 — the telemetry study lands (3.2x)
  [5, 'twitter', 'CREATE_POST', {
    content: "Releasing the Helios Research telemetry study today: agent-native teams in the latest batch shipped 3.2× more weekly releases in their first 12 weeks than traditional teams. This is the strongest efficiency signal we've measured on any cohort."
  }],
  [9, 'twitter', 'CREATE_COMMENT', {
    content: "3.2× is the number every AGI-native founder is about to have on a slide by tomorrow morning. Running Wen's full study in The Batch Report tonight.",
    post_id: 'post_4017',
    post_author_name: 'Dr. Wen Zhao',
    post_content: "agent-native teams in the latest batch shipped 3.2× more weekly releases in their first 12 weeks than traditional teams."
  }],
  [8, 'twitter', 'QUOTE_POST', {
    quote_content: '3.2x is exactly the number we\'ve been saying since day one. Velocity\'s cohort hits similar multiples with zero committee overhead. Move faster, YC.',
    original_content: 'agent-native teams in the latest batch shipped 3.2× more weekly releases in their first 12 weeks than traditional teams.',
    original_author_name: 'Dr. Wen Zhao'
  }],
  [7, 'twitter', 'LIKE_POST', {
    post_author_name: 'Dr. Wen Zhao',
    post_content: "agent-native teams in the latest batch shipped 3.2× more weekly releases in their first 12 weeks than traditional teams."
  }],
  [11, 'reddit', 'CREATE_POST', {
    content: "Before everyone gets carried away with 3.2x: the post-batch quality audit tells a different story. Once you control for senior oversight and clear ownership, the real gap is 1.4x, not 3.2x. And agent-heavy teams without oversight showed 2.4x more critical production incidents. Speed without judgment is not the same as speed."
  }],
  [10, 'reddit', 'CREATE_COMMENT', {
    content: "This is the number that should actually change the selection rubric. 1.4x with proper oversight is still a real edge, but it's a founder-quality story, not a headcount-replacement story.",
    post_id: 'post_4018',
    post_author_name: 'Aisha Rahman',
    post_content: "Once you control for senior oversight and clear ownership, the real gap is 1.4x, not 3.2x. Agent-heavy teams without oversight showed 2.4x more critical production incidents."
  }],
  [12, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Jonah Price',
    post_content: "This is the number that should actually change the selection rubric. 1.4x with proper oversight is still a real edge, but it's a founder-quality story, not a headcount-replacement story."
  }],
  [4, 'reddit', 'CREATE_POST', {
    content: "1.4x with fewer incidents sounds a lot more like what we're actually seeing at Parallel Desk than the 3.2x headline. Grateful someone finally published the number that matches reality on the ground."
  }],

  // Round 8 — the evidence clash plays out publicly
  [2, 'twitter', 'CREATE_POST', {
    content: "Both studies are real and both matter: 3.2× raw velocity is the ceiling agent leverage makes possible; 1.4× is what teams without oversight competence actually capture, with 2.4× more incidents to show for the gap. The selection question isn't agents vs. no agents. It's whether we can select for the oversight."
  }],
  [1, 'twitter', 'CREATE_COMMENT', {
    content: "This is the read that matters. The gap between 3.2x and 1.4x isn't a reason to avoid agent-native teams — it's the exact reason admissions needs a real interview for judgment, not just a fleet-size checkbox.",
    post_id: 'post_4019',
    post_author_name: 'Priya Shenoy',
    post_content: "3.2× raw velocity is the ceiling agent leverage makes possible; 1.4× is what teams without oversight competence actually capture."
  }],
  [3, 'twitter', 'CREATE_POST', {
    content: "For what it's worth, I'm the 40-agent solo-founder example people keep citing, and I'll say plainly: the 2.4x incident number doesn't surprise me. I spend more hours reviewing agent output than most nine-person teams spend writing code. That's the part of my routine nobody screenshots."
  }],
  [9, 'twitter', 'REPOST', {
    original_author_name: 'Kai Nakamura',
    original_content: "the 2.4x incident number doesn't surprise me. I spend more hours reviewing agent output than most nine-person teams spend writing code."
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: "Kai's tweet about spending more hours reviewing agent output than most nine-person teams spend writing code is the most useful thing said in this entire fight. 'Agent-native' should mean 'reviews constantly,' not 'never reviews.'"
  }],
  [14, 'reddit', 'SEARCH_POSTS', { query: 'agent leverage supervision competence interview rubric' }],
  [12, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Tomas Lindqvist',
    post_content: "Kai's tweet about spending more hours reviewing agent output than most nine-person teams spend writing code is the most useful thing said in this entire fight."
  }],
  [11, 'reddit', 'CREATE_COMMENT', {
    content: "Exactly the distinction I've been trying to get YC to write into the rubric. If the interview can't tell a reviewing founder from a non-reviewing one, ≥10:1 leverage is a vanity number.",
    post_id: 'post_4020',
    post_author_name: 'Tomas Lindqvist',
    post_content: "Kai's tweet about spending more hours reviewing agent output than most nine-person teams spend writing code is the most useful thing said in this entire fight."
  }],

  // Round 9 — convergence begins, Elena signals the pilot
  [0, 'twitter', 'CREATE_POST', {
    content: "Where we've landed: a staged AGI-Native Track for roughly sixty companies, about 15% of the batch, evaluated over two full batch cycles before any wider commitment. Full overhaul stays off the table unless the pilot clears its own bar. Applications for Winter 2027 open in September."
  }],
  [7, 'twitter', 'QUOTE_POST', {
    quote_content: 'This is the structure our committee can actually underwrite. A bounded pilot with a real evaluation window is a different risk than a blanket policy change.',
    original_content: 'a staged AGI-Native Track for roughly sixty companies, about 15% of the batch, evaluated over two full batch cycles before any wider commitment.',
    original_author_name: 'Elena Voss'
  }],
  [9, 'twitter', 'LIKE_POST', {
    post_author_name: 'Elena Voss',
    post_content: "a staged AGI-Native Track for roughly sixty companies, about 15% of the batch, evaluated over two full batch cycles before any wider commitment."
  }],
  [8, 'twitter', 'DO_NOTHING', {}],
  [6, 'reddit', 'CREATE_POST', {
    content: "Sixty companies and a two-cycle evaluation window is a number I can actually plan around instead of guessing at. AgentForge will apply for the pilot track the day applications open."
  }],
  [4, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Tomas Lindqvist',
    post_content: "Sixty companies and a two-cycle evaluation window is a number I can actually plan around instead of guessing at."
  }],
  [10, 'reddit', 'CREATE_COMMENT', {
    content: "Evalio's applying too. If the rubric actually screens for supervision competence like Aisha's been arguing, this could be the first cohort where 'agent-native' means something more specific than 'has API keys.'",
    post_id: 'post_4021',
    post_author_name: 'Tomas Lindqvist',
    post_content: "Sixty companies and a two-cycle evaluation window is a number I can actually plan around instead of guessing at."
  }],
  [14, 'reddit', 'FOLLOW', { target_user: 'elena_voss_ycagi' }],

  // Round 10 — settling into pragmatism
  [0, 'twitter', 'CREATE_POST', {
    content: "One week into finalizing the AGI-Native Track: $25M committed, six partners and program managers staffed through mid-2027, and a pause trigger if incident rates exceed 1.5x baseline. This is the version of 'betting on AGI' I can defend to every LP in the room."
  }],
  [1, 'twitter', 'CREATE_COMMENT', {
    content: "Six partners staffed and a pause trigger written down before a single company is admitted — that's the guardrail I was asking for back in round five. Comfortable signing off on this.",
    post_id: 'post_4022',
    post_author_name: 'Elena Voss',
    post_content: "One week into finalizing the AGI-Native Track: $25M committed, six partners and program managers staffed through mid-2027, and a pause trigger if incident rates exceed 1.5x baseline."
  }],
  [2, 'twitter', 'QUOTE_POST', {
    quote_content: 'Worth remembering this could have gone the other way — either a rushed full overhaul or a defensive do-nothing. It landed here because the evidence fight in weeks 7 and 8 actually got resolved instead of ignored.',
    original_content: "One week into finalizing the AGI-Native Track: $25M committed, six partners and program managers staffed through mid-2027, and a pause trigger if incident rates exceed 1.5x baseline.",
    original_author_name: 'Elena Voss'
  }],
  [13, 'twitter', 'LIKE_POST', {
    post_author_name: 'Elena Voss',
    post_content: "One week into finalizing the AGI-Native Track: $25M committed, six partners and program managers staffed through mid-2027, and a pause trigger if incident rates exceed 1.5x baseline."
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: "Closing thought from AgentForge: the pause trigger is what makes this credible. A program that can't reverse itself was always going to get the incident-rate debate wrong eventually. Glad YC built the exit ramp before the entrance."
  }],
  [4, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Tomas Lindqvist',
    post_content: "the pause trigger is what makes this credible. A program that can't reverse itself was always going to get the incident-rate debate wrong eventually."
  }],
  [11, 'reddit', 'CREATE_COMMENT', {
    content: "Filing this under 'the outcome I actually wanted three weeks ago and didn't think I'd get.' Oversight competence made it into the rubric instead of getting hand-waved away.",
    post_id: 'post_4023',
    post_author_name: 'Tomas Lindqvist',
    post_content: "the pause trigger is what makes this credible."
  }],
  [14, 'reddit', 'DO_NOTHING', {}]
]

// 80 actions over the locked 40-round demo run: 2 actions surface per round.
const ACTIONS_PER_ROUND = 2

const actions = RAW.map((row, index) => {
  const [agentId, platform, actionType, actionArgs] = row
  const roundNum = Math.floor(index / ACTIONS_PER_ROUND) + 1
  const agent = byId(agentId)

  return {
    id: `act_${index + 1}`,
    timestamp: ts(index * 8),
    platform,
    agent_id: agentId,
    agent_name: agent.name,
    action_type: actionType,
    round_num: roundNum,
    action_args: actionArgs
  }
})

export default actions
