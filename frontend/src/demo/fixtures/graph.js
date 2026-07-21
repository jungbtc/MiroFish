// Demo fixture: the Y Combinator / AGI-era knowledge graph returned by
// /api/graph/data/:graphId (progressively, per src/demo/handlers/phase12.js)
// and, once fully built, rendered by src/components/GraphPanel.vue.
//
// Node/edge shape mirrors what GraphPanel.vue reads directly off each item:
// node.uuid, node.name, node.labels (['Entity', '<Type>']), node.attributes
// (plain key/value object), node.summary, node.created_at; edge.uuid,
// edge.source_node_uuid, edge.target_node_uuid, edge.name, edge.fact,
// edge.fact_type, edge.episodes, edge.created_at, edge.valid_at.
//
// Node creation order below doubles as reveal order for the progressive
// graph-build animation (src/demo/handlers/phase12.js sorts by created_at
// and reveals ceil(fraction * total)), so it's deliberately "core entities
// first, periphery later": Y Combinator, its partners, the AGI-Native Track
// pilot, and the founders/startups at the center of the funding decision
// surface early; research labs, LPs, the rival accelerator, media, and
// community voices fill in afterward.

import { ts } from './scenario.js'

const BATCH_COMPOSITION_STUDY = 'yc_batch_composition_2023_2026.pdf'
const TELEMETRY_STUDY = 'agent_leverage_telemetry_study.pdf'
const QUALITY_AUDIT = 'post_batch_quality_audit.md'

// --- Node roster --------------------------------------------------------
// Index in this array determines created_at (ts(idx * 20)) and therefore
// reveal order.
const NODE_DEFS = [
  // Y Combinator org + pilot program
  { id: 'yc', name: 'Y Combinator', type: 'AcceleratorProgram',
    attributes: { industry: 'Startup Accelerator', headquarters: 'Mountain View, California', founded: '2005', batches_per_year: '2' },
    summary: 'Leading startup accelerator deciding whether to commit to a full AGI-native overhaul of its batch model, stage a reversible AGI-Native Track pilot, or keep the classic playbook for Winter 2027.' },
  { id: 'agi_native_track', name: 'AGI-Native Track', type: 'AcceleratorProgram',
    attributes: { program_type: 'Pilot Track', capacity: '60 companies (~15% of batch)', duration: '2 batch cycles', budget_usd: '$25,000,000' },
    summary: 'Proposed reversible pilot admitting 60 agent-native companies over two batch cycles, backed by $25M and staffed by 6 partners through 2027-06-30, before any full commitment.' },
  { id: 'yc_selection_committee', name: 'YC Selection Committee', type: 'Partner',
    attributes: { role: 'Governance Body', size: '6 partners' },
    summary: 'Cross-partner body evaluating whether the AGI-Native Track pilot should expand into a full batch-model overhaul ahead of the 2026-08-15 go/no-go decision.' },

  // Partners
  { id: 'elena_voss', name: 'Elena Voss', type: 'Partner',
    attributes: { role: 'Group Partner', employer: 'Y Combinator', tenure: '5 years' },
    summary: 'Group Partner leading the AGI-Native Track; the pragmatic champion of a staged, reversible pilot over a full batch-model overhaul.' },
  { id: 'marcus_oyelaran', name: 'Marcus Oyelaran', type: 'Partner',
    attributes: { role: 'Managing Partner', employer: 'Y Combinator', tenure: '9 years' },
    summary: "Managing Partner protecting YC's brand; demands reversibility, pause triggers, and guardrails before any AGI-native expansion." },
  { id: 'priya_shenoy', name: 'Priya Shenoy', type: 'Partner',
    attributes: { role: 'Visiting Partner', employer: 'Y Combinator', background: 'ex-frontier-lab researcher' },
    summary: 'Visiting Partner and former frontier-lab researcher who translates capability curves into concrete batch-strategy recommendations.' },

  // Founders + startups
  { id: 'kai_nakamura', name: 'Kai Nakamura', type: 'Founder',
    attributes: { role: 'Solo Founder', company: 'Loomfield', agent_fleet_size: '40 agents', arr_usd: '$2,100,000' },
    summary: 'Solo founder running a 40-agent fleet to $2.1M ARR alone -- the archetype of the agent-native applicant profile YC is debating whether to prioritize.' },
  { id: 'loomfield', name: 'Loomfield', type: 'StartupCompany',
    attributes: { industry: 'Vertical SaaS (Property Management)', team_size: '1 (solo founder + agent fleet)', agent_leverage_ratio: '40:1' },
    summary: 'Solo-founder vertical SaaS company run almost entirely by a 40-agent fleet, cited as the clearest example of the >=10:1 agent-leverage applicant profile.' },
  { id: 'sofia_marek', name: 'Sofia Marek', type: 'Founder',
    attributes: { role: 'Co-founder', company: 'Parallel Desk', team_size: '9' },
    summary: 'Co-founder of a traditional nine-person B2B SaaS team who feels the selection ground shifting under her as agent-native applicants dominate the conversation.' },
  { id: 'parallel_desk', name: 'Parallel Desk', type: 'StartupCompany',
    attributes: { industry: 'B2B SaaS (Workflow Software)', team_size: '9', agent_leverage_ratio: '1.5:1' },
    summary: "Traditional-headcount B2B SaaS company whose hiring-based playbook looks increasingly out of step with YC's proposed agent-leverage criteria." },
  { id: 'tomas_lindqvist', name: 'Tomas Lindqvist', type: 'Founder',
    attributes: { role: 'CTO', company: 'AgentForge' },
    summary: 'CTO of an agent-infrastructure startup whose tooling underpins several other AGI-native applicants in the batch.' },
  { id: 'agentforge', name: 'AgentForge', type: 'StartupCompany',
    attributes: { industry: 'Agent Infrastructure', team_size: '4', agent_leverage_ratio: '12:1' },
    summary: 'Agent-infrastructure startup supplying orchestration tooling to Loomfield, Evalio, and other agent-native applicants.' },
  { id: 'jonah_price', name: 'Jonah Price', type: 'Founder',
    attributes: { role: 'Founder', company: 'Evalio', background: 'PhD dropout' },
    summary: 'PhD-dropout founder of an agent-evals startup, building the benchmarking tools YC partners increasingly cite in interviews.' },
  { id: 'evalio', name: 'Evalio', type: 'StartupCompany',
    attributes: { industry: 'Agent Evaluation & Benchmarking', team_size: '3', agent_leverage_ratio: '9:1' },
    summary: "Agent-evals startup whose benchmarks feed directly into the taste/judgment criterion of YC's proposed applicant rubric." },
  { id: 'leo_martins', name: 'Leo Martins', type: 'Founder',
    attributes: { role: 'Founder', company: 'Quiet Systems', background: 'second-time founder, exited 2024' },
    summary: 'Second-time founder now building agent-native after a 2024 exit; mentors first-time founders navigating the shift to tiny, agent-leveraged teams.' },
  { id: 'quiet_systems', name: 'Quiet Systems', type: 'StartupCompany',
    attributes: { industry: 'Agent-native Ops Tooling', team_size: '2', agent_leverage_ratio: '15:1' },
    summary: 'Two-person agent-native operations startup built by a repeat founder, held up as a model for the AGI-Native Track curriculum.' },
  { id: 'gabe_torres', name: 'Gabe Torres', type: 'Founder',
    attributes: { role: 'Indie Founder', company: 'Fieldnote', background: 'indie hacker, viral consumer agent apps' },
    summary: 'Indie hacker behind several viral consumer agent apps, publicly skeptical that accelerators add value for agent-native solo builders.' },
  { id: 'fieldnote', name: 'Fieldnote', type: 'StartupCompany',
    attributes: { industry: 'Consumer Agent Apps', team_size: '1', agent_leverage_ratio: '20:1' },
    summary: 'Viral consumer note-taking app built solo with a large agent fleet, cited as evidence that distribution instinct can outweigh formal accelerator backing.' },
  { id: 'amara_fields', name: 'Amara Fields', type: 'Founder',
    attributes: { role: 'Founder', company: 'Driftless Bio' },
    summary: 'Founder applying agent-native drug-discovery workflows to a traditionally headcount-heavy biotech domain.' },
  { id: 'driftless_bio', name: 'Driftless Bio', type: 'StartupCompany',
    attributes: { industry: 'Agent-native Biotech', team_size: '5', agent_leverage_ratio: '4:1' },
    summary: 'Agent-augmented biotech startup testing how far agent leverage extends into wet-lab-adjacent, regulation-heavy domains.' },
  { id: 'owen_brandt', name: 'Owen Brandt', type: 'Founder',
    attributes: { role: 'Founder', company: 'Cobalt Ledger' },
    summary: 'Founder of an agent-native fintech startup often cited in partner interviews as a borderline case between taste and pure automation.' },
  { id: 'cobalt_ledger', name: 'Cobalt Ledger', type: 'StartupCompany',
    attributes: { industry: 'Agent-native Fintech', team_size: '3', agent_leverage_ratio: '8:1' },
    summary: 'Agent-native ledger-reconciliation startup whose rapid shipping pace has drawn both praise and oversight concerns.' },

  // Research labs
  { id: 'wen_zhao', name: 'Dr. Wen Zhao', type: 'ResearchLab',
    attributes: { role: 'Researcher', employer: 'Helios Research' },
    summary: 'Frontier-lab researcher publishing capability-curve and telemetry data showing agent-native teams shipped 3.2x more weekly releases in their first 12 weeks.' },
  { id: 'helios_research', name: 'Helios Research', type: 'ResearchLab',
    attributes: { industry: 'Frontier AI Research Lab' },
    summary: 'Frontier AI research lab behind the agent-leverage telemetry study central to the pilot debate.' },
  { id: 'aisha_rahman', name: 'Aisha Rahman', type: 'ResearchLab',
    attributes: { role: 'Alignment & Safety Researcher', employer: 'Cascade AI Lab' },
    summary: 'Safety researcher arguing that selection criteria must weigh oversight competence, citing 2.4x more critical production incidents in agent-heavy teams without senior oversight.' },
  { id: 'cascade_ai_lab', name: 'Cascade AI Lab', type: 'ResearchLab',
    attributes: { industry: 'AI Safety & Evaluation Lab' },
    summary: 'Research lab behind the conflicting post-batch quality audit finding only a 1.4x output gain and elevated incident rates.' },

  // LPs
  { id: 'rachel_adeyemi', name: 'Rachel Adeyemi', type: 'InvestorLP',
    attributes: { role: 'Limited Partner', employer: 'Crestline University Endowment' },
    summary: 'University-endowment LP skeptical that accelerator returns hold up in the AGI era if batch composition shifts too far from proven team structures.' },
  { id: 'crestline_endowment', name: 'Crestline University Endowment', type: 'InvestorLP',
    attributes: { investor_type: 'University Endowment' },
    summary: "Limited partner in Y Combinator's fund, weighing return expectations against the risk of an unproven AGI-native batch model." },
  { id: 'nadia_petrova', name: 'Nadia Petrova', type: 'InvestorLP',
    attributes: { role: 'Early-stage VC Analyst' },
    summary: 'Analyst at a seed-stage fund tracking how agent leverage is already reshaping seed-market valuations and check sizes.' },
  { id: 'anchorpoint_ventures', name: 'Anchorpoint Ventures', type: 'InvestorLP',
    attributes: { investor_type: 'Early-stage Venture Fund' },
    summary: 'Seed-stage fund adjusting its own diligence criteria in response to the agent-leverage ratios coming out of recent YC batches.' },
  { id: 'lp_advisory_council', name: 'LP Advisory Council', type: 'InvestorLP',
    attributes: { role: 'Cross-LP Governance Body' },
    summary: "Joint council coordinating limited-partner positions ahead of Y Combinator's go/no-go decision on the AGI-Native Track." },

  // Rival accelerator
  { id: 'dev_kapoor', name: 'Dev Kapoor', type: 'AcceleratorProgram',
    attributes: { role: 'Partner', employer: 'Velocity Program' },
    summary: "Rival-accelerator partner publicly mocking YC's caution and running an all-in AGI-native track of his own." },
  { id: 'velocity_program', name: 'Velocity Program', type: 'AcceleratorProgram',
    attributes: { industry: 'Startup Accelerator (rival)', focus_area: 'All-in AGI-native batches' },
    summary: "Rival accelerator running an all-in AGI-native track, positioning itself against YC's more cautious staged approach." },

  // Media
  { id: 'maya_chen', name: 'Maya Chen', type: 'MediaOutlet',
    attributes: { role: 'Journalist', employer: 'The Batch Report' },
    summary: "Journalist whose leaked-memo story broke the news that YC is drafting an AGI-Native Track, driving the discourse from day one." },
  { id: 'batch_report', name: 'The Batch Report', type: 'MediaOutlet',
    attributes: { industry: 'Startup & Accelerator Trade Press' },
    summary: 'Trade outlet that broke the AGI-Native Track leak, sending #AGInativeYC trending within hours.' },
  { id: 'frontier_signal', name: 'Frontier Signal', type: 'MediaOutlet',
    attributes: { industry: 'AI Industry Newsletter' },
    summary: 'Newsletter tracking LP, partner, and rival-accelerator reactions to the AGI-Native Track story as it develops.' },
  { id: 'founder_wire', name: 'Founder Wire', type: 'MediaOutlet',
    attributes: { industry: 'Founder Community Trade Press' },
    summary: 'Trade publication covering founder sentiment across both agent-native and traditional-team applicants.' },

  // Enterprise buyer / community voices
  { id: 'hana_sato', name: 'Hana Sato', type: 'EnterpriseBuyer',
    attributes: { role: 'Chief Information Officer', employer: 'Ashford Retail Group' },
    summary: 'Fortune-500 retail CIO representing the demand side: procurement already assumes agent-augmented vendor teams, not headcount.' },
  { id: 'ashford_retail', name: 'Ashford Retail Group', type: 'EnterpriseBuyer',
    attributes: { industry: 'Fortune-500 Retail' },
    summary: "Enterprise buyer organization whose procurement standards are shifting to reward agent leverage in vendor selection." },
  { id: 'enterprise_procurement_roundtable', name: 'Enterprise Procurement Roundtable', type: 'EnterpriseBuyer',
    attributes: { role: 'Cross-enterprise Buyer Group' },
    summary: 'Group of enterprise buyers comparing notes on evaluating agent-native vendors coming out of accelerator batches.' },
  { id: 'indie_builders_collective', name: 'Indie Builders Collective', type: 'FounderCommunity',
    attributes: { role: 'Community Forum' },
    summary: 'Online community of solo and small-team agent-native builders debating whether accelerator backing still matters.' },
  { id: 'winter2027_applicant_pool', name: 'Winter 2027 Applicant Pool', type: 'FounderCommunity',
    attributes: { role: 'Prospective Applicant Community' },
    summary: "Prospective Winter 2027 applicants speculating about how the AGI-Native Track pilot will change YC's admission bar." }
]

const NODE_SECONDS_STEP = 20

const nodeIndex = new Map(NODE_DEFS.map((def, idx) => [def.id, idx]))

export const nodes = NODE_DEFS.map((def, idx) => ({
  uuid: `node_${def.id}`,
  name: def.name,
  labels: ['Entity', def.type],
  attributes: def.attributes,
  summary: def.summary,
  created_at: ts(idx * NODE_SECONDS_STEP)
}))

// --- Edges ---------------------------------------------------------------
// `source`/`target` reference NODE_DEFS ids above; created_at/valid_at are
// derived so created_at is always >= both endpoints' created_at (required
// for coherent progressive reveal).
const EDGE_DEFS = [
  // YC governance / pilot design cluster
  { source: 'elena_voss', target: 'yc', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Elena Voss serves as Group Partner at Y Combinator and leads the AGI-Native Track.' },
  { source: 'marcus_oyelaran', target: 'yc', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Marcus Oyelaran serves as Managing Partner at Y Combinator, protecting the brand and demanding reversibility on any AGI-native expansion.' },
  { source: 'priya_shenoy', target: 'yc', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Priya Shenoy serves as Visiting Partner at Y Combinator, translating frontier capability curves into batch strategy.' },
  { source: 'elena_voss', target: 'agi_native_track', name: 'LEADS_INITIATIVE', fact_type: 'governance',
    fact: 'Elena Voss leads the AGI-Native Track pilot design, championing a staged, reversible rollout over a full batch-model overhaul.' },
  { source: 'marcus_oyelaran', target: 'agi_native_track', name: 'OVERSEES', fact_type: 'governance',
    fact: "Marcus Oyelaran oversees the AGI-Native Track's guardrails, requiring pause/reverse triggers before any expansion beyond the pilot." },
  { source: 'yc_selection_committee', target: 'yc', name: 'OVERSEES', fact_type: 'governance',
    fact: 'The YC Selection Committee, including Elena Voss and Marcus Oyelaran, must ratify a go/no-go decision on the AGI-Native Track by 2026-08-15, ahead of Winter 2027 applications opening in September 2026.' },
  { source: 'yc', target: 'agi_native_track', name: 'FUNDS', fact_type: 'pilot_program', episodes: [BATCH_COMPOSITION_STUDY],
    fact: 'Y Combinator has committed $25M, binding and staffed by 6 partners and program managers, to the AGI-Native Track pilot through 2027-06-30.' },
  { source: 'yc_selection_committee', target: 'agi_native_track', name: 'EVALUATES', fact_type: 'applicant_profile',
    fact: 'The YC Selection Committee is evaluating the AGI-Native Track -- 60 companies (~15% of the batch) over 2 batch cycles -- screening for agent leverage, taste and judgment artifacts, and distribution instinct, while flagging headcount-as-progress, demo-only agents, and no owned distribution as anti-patterns.' },
  { source: 'priya_shenoy', target: 'agi_native_track', name: 'ADVISES', fact_type: 'governance',
    fact: "Priya Shenoy translates frontier capability curves into the AGI-Native Track's curriculum design." },
  { source: 'agi_native_track', target: 'yc', name: 'REPORTS_BATCH_COMPOSITION', fact_type: 'batch_data', episodes: [BATCH_COMPOSITION_STUDY],
    fact: "In the most recent batch, 41% of companies used agent fleets for the majority of engineering work (up from 9% two batches earlier), and median founding-team size fell to 1.8 people, down from 3.1 in 2023." },

  // Partner / founder mentorship cluster
  { source: 'elena_voss', target: 'kai_nakamura', name: 'MENTORS', fact_type: 'mentorship',
    fact: 'Elena Voss mentors Kai Nakamura as the clearest agent-native applicant archetype under consideration for the AGI-Native Track.' },
  { source: 'elena_voss', target: 'sofia_marek', name: 'MENTORS', fact_type: 'mentorship',
    fact: "Elena Voss also mentors Sofia Marek, whose traditional nine-person team represents the classic-playbook comparison case." },
  { source: 'marcus_oyelaran', target: 'tomas_lindqvist', name: 'MENTORS', fact_type: 'mentorship',
    fact: "Marcus Oyelaran mentors Tomas Lindqvist on scaling AgentForge's infrastructure responsibly across the batch." },
  { source: 'priya_shenoy', target: 'jonah_price', name: 'MENTORS', fact_type: 'mentorship',
    fact: "Priya Shenoy mentors Jonah Price on translating Evalio's benchmark work into partner-interview criteria." },
  { source: 'leo_martins', target: 'gabe_torres', name: 'MENTORS', fact_type: 'mentorship',
    fact: 'Leo Martins, a second-time founder, mentors Gabe Torres on turning viral consumer traction into a durable company.' },
  { source: 'leo_martins', target: 'jonah_price', name: 'MENTORS', fact_type: 'mentorship',
    fact: 'Leo Martins also mentors Jonah Price on hiring judgment as Evalio scales past three people.' },
  { source: 'elena_voss', target: 'leo_martins', name: 'MENTORS', fact_type: 'mentorship',
    fact: 'Elena Voss consults Leo Martins informally as a repeat founder proof point for the agent-native curriculum.' },

  // Founder / startup cluster
  { source: 'kai_nakamura', target: 'loomfield', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Kai Nakamura is the solo founder of Loomfield, running a 40-agent fleet to $2.1M ARR alone.' },
  { source: 'sofia_marek', target: 'parallel_desk', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Sofia Marek co-founded Parallel Desk, a traditional nine-person B2B SaaS team.' },
  { source: 'tomas_lindqvist', target: 'agentforge', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Tomas Lindqvist serves as CTO of AgentForge, the agent-infrastructure startup underpinning several other applicants.' },
  { source: 'jonah_price', target: 'evalio', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Jonah Price founded Evalio after leaving his PhD program to build agent-evals tooling full time.' },
  { source: 'leo_martins', target: 'quiet_systems', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Leo Martins founded Quiet Systems after exiting his previous company in 2024.' },
  { source: 'gabe_torres', target: 'fieldnote', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Gabe Torres built Fieldnote solo, an indie consumer agent app that went viral without formal accelerator backing.' },
  { source: 'amara_fields', target: 'driftless_bio', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Amara Fields founded Driftless Bio to test agent-native workflows in a traditionally headcount-heavy biotech domain.' },
  { source: 'owen_brandt', target: 'cobalt_ledger', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Owen Brandt founded Cobalt Ledger, an agent-native fintech startup shipping reconciliation features weekly.' },
  { source: 'loomfield', target: 'agentforge', name: 'BUILDS_WITH', fact_type: 'product_collaboration',
    fact: "Loomfield builds its 40-agent fleet orchestration directly on AgentForge's infrastructure." },
  { source: 'evalio', target: 'agentforge', name: 'BUILDS_WITH', fact_type: 'product_collaboration',
    fact: "Evalio builds its benchmarking harness on AgentForge's agent-orchestration primitives." },
  { source: 'quiet_systems', target: 'agentforge', name: 'BUILDS_WITH', fact_type: 'product_collaboration',
    fact: 'Quiet Systems runs its two-person operations stack on AgentForge infrastructure.' },
  { source: 'cobalt_ledger', target: 'evalio', name: 'BUILDS_WITH', fact_type: 'product_collaboration',
    fact: "Cobalt Ledger uses Evalio's benchmarks to evaluate its own reconciliation agents before shipping." },
  { source: 'driftless_bio', target: 'helios_research', name: 'BUILDS_WITH', fact_type: 'product_collaboration',
    fact: 'Driftless Bio collaborates with Helios Research on agent-native lab-workflow benchmarks.' },
  { source: 'kai_nakamura', target: 'yc', name: 'DEMONSTRATES_APPLICANT_PROFILE_FOR', fact_type: 'applicant_profile',
    fact: "Kai Nakamura's 40:1 agent-leverage ratio is cited internally as the clearest example of the >=10:1 threshold in YC's proposed applicant profile." },
  { source: 'sofia_marek', target: 'yc', name: 'RAISES_CONCERN_ABOUT', fact_type: 'applicant_profile',
    fact: 'Sofia Marek worries that weighting agent leverage over headcount could push traditional teams like Parallel Desk out of future batches.' },

  // Research lab cluster (the evidence conflict)
  { source: 'wen_zhao', target: 'helios_research', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Dr. Wen Zhao is a researcher at Helios Research.' },
  { source: 'aisha_rahman', target: 'cascade_ai_lab', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Aisha Rahman is an alignment and safety researcher at Cascade AI Lab.' },
  { source: 'helios_research', target: 'yc', name: 'PUBLISHES', fact_type: 'research_publication', episodes: [TELEMETRY_STUDY],
    fact: 'Helios Research published the agent leverage telemetry study, finding agent-native teams shipped 3.2x more weekly releases than traditional teams in their first 12 weeks.' },
  { source: 'cascade_ai_lab', target: 'yc', name: 'PUBLISHES', fact_type: 'research_publication', episodes: [QUALITY_AUDIT],
    fact: 'Cascade AI Lab published the post-batch quality audit, finding only a 1.4x output gain for agent-native teams and attributing the gap to missing senior oversight and unclear ownership.' },
  { source: 'cascade_ai_lab', target: 'yc', name: 'WARNS', fact_type: 'evidence_dispute', episodes: [QUALITY_AUDIT],
    fact: "Cascade AI Lab's post-batch audit also flags 2.4x more critical production incidents in agent-heavy teams that lack senior oversight." },
  { source: 'wen_zhao', target: 'aisha_rahman', name: 'DISPUTES_FINDINGS_OF', fact_type: 'evidence_dispute',
    fact: "Dr. Wen Zhao publicly disputes Aisha Rahman's post-batch audit findings, arguing the incident-rate spike reflects rollout mistakes rather than a hard ceiling on agent leverage." },
  { source: 'aisha_rahman', target: 'elena_voss', name: 'DEBATES_WITH', fact_type: 'debate',
    fact: 'Aisha Rahman debates Elena Voss publicly, insisting selection criteria must weigh oversight competence alongside agent leverage.' },
  { source: 'priya_shenoy', target: 'wen_zhao', name: 'CITES', fact_type: 'research_publication', episodes: [TELEMETRY_STUDY],
    fact: "Priya Shenoy cites Dr. Wen Zhao's capability-curve data directly in her batch-strategy recommendations to the Selection Committee." },
  { source: 'helios_research', target: 'agi_native_track', name: 'INFORMS_CURRICULUM_OF', fact_type: 'research_publication', episodes: [TELEMETRY_STUDY],
    fact: "Helios Research's capability-curve data directly informs the AGI-Native Track's proposed curriculum." },
  { source: 'cascade_ai_lab', target: 'yc_selection_committee', name: 'RAISES_CONCERN_ABOUT', fact_type: 'evidence_dispute', episodes: [QUALITY_AUDIT],
    fact: "Cascade AI Lab raised its incident-rate findings directly with the YC Selection Committee ahead of the go/no-go decision." },

  // LP cluster
  { source: 'rachel_adeyemi', target: 'crestline_endowment', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Rachel Adeyemi serves as a limited partner representative for Crestline University Endowment.' },
  { source: 'nadia_petrova', target: 'anchorpoint_ventures', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Nadia Petrova is an early-stage analyst at Anchorpoint Ventures.' },
  { source: 'crestline_endowment', target: 'yc', name: 'FUNDS', fact_type: 'lp_relations',
    fact: "Crestline University Endowment is a limited partner in Y Combinator's fund, questioning whether accelerator returns hold up if batch composition shifts too far from proven team structures." },
  { source: 'rachel_adeyemi', target: 'elena_voss', name: 'DEBATES_WITH', fact_type: 'debate',
    fact: "Rachel Adeyemi debates Elena Voss over whether admitting far more tiny agent-augmented teams dilutes the fund's return profile." },
  { source: 'lp_advisory_council', target: 'yc', name: 'EVALUATES', fact_type: 'lp_relations',
    fact: "The LP Advisory Council is coordinating a unified limited-partner position ahead of Y Combinator's 2026-08-15 go/no-go decision." },
  { source: 'rachel_adeyemi', target: 'lp_advisory_council', name: 'MEMBER_OF', fact_type: 'lp_relations',
    fact: 'Rachel Adeyemi sits on the LP Advisory Council representing endowment-class limited partners.' },
  { source: 'nadia_petrova', target: 'lp_advisory_council', name: 'MEMBER_OF', fact_type: 'lp_relations',
    fact: 'Nadia Petrova participates in LP Advisory Council discussions tracking seed-market shifts driven by agent leverage.' },
  { source: 'nadia_petrova', target: 'loomfield', name: 'ANALYZES', fact_type: 'lp_relations',
    fact: "Nadia Petrova analyzes Loomfield's solo-founder economics as a bellwether for how agent leverage is reshaping seed-stage valuations." },

  // Rival accelerator cluster
  { source: 'dev_kapoor', target: 'velocity_program', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Dev Kapoor is a partner at Velocity Program.' },
  { source: 'velocity_program', target: 'yc', name: 'COMPETES_WITH', fact_type: 'competitive_dynamics',
    fact: 'Velocity Program competes directly with Y Combinator for agent-native applicant deal flow.' },
  { source: 'dev_kapoor', target: 'yc', name: 'MOCKS', fact_type: 'competitive_dynamics',
    fact: "Dev Kapoor publicly mocks Y Combinator's staged caution, running an all-in AGI-native track of his own at Velocity Program." },
  { source: 'velocity_program', target: 'kai_nakamura', name: 'RECRUITS', fact_type: 'recruiting',
    fact: 'Velocity Program has approached Kai Nakamura directly, positioning itself as the faster-moving home for agent-native solo founders.' },
  { source: 'velocity_program', target: 'gabe_torres', name: 'RECRUITS', fact_type: 'recruiting',
    fact: 'Velocity Program has also approached Gabe Torres, betting that indie agent-native builders will skip traditional accelerators entirely.' },
  { source: 'dev_kapoor', target: 'agi_native_track', name: 'CRITIQUES', fact_type: 'competitive_dynamics',
    fact: "Dev Kapoor publicly critiques the AGI-Native Track's 60-company cap as too cautious given how fast agent leverage is compounding." },

  // Media cluster
  { source: 'maya_chen', target: 'batch_report', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Maya Chen is a journalist at The Batch Report.' },
  { source: 'batch_report', target: 'agi_native_track', name: 'BREAKS_STORY_ON', fact_type: 'media_coverage',
    fact: 'The Batch Report broke the story that Y Combinator is drafting an AGI-Native Track, sending #AGInativeYC trending within hours.' },
  { source: 'maya_chen', target: 'yc', name: 'REPORTS_ON', fact_type: 'media_coverage',
    fact: "Maya Chen's leaked-memo reporting on Y Combinator's AGI-native plans drives the discourse from day one." },
  { source: 'frontier_signal', target: 'yc', name: 'REPORTS_ON', fact_type: 'media_coverage',
    fact: 'Frontier Signal tracks LP, partner, and rival-accelerator reactions to the AGI-Native Track story as it develops.' },
  { source: 'founder_wire', target: 'kai_nakamura', name: 'REPORTS_ON', fact_type: 'media_coverage',
    fact: 'Founder Wire profiled Kai Nakamura as the poster child of the agent-native applicant wave.' },
  { source: 'batch_report', target: 'wen_zhao', name: 'CITES', fact_type: 'media_coverage', episodes: [TELEMETRY_STUDY],
    fact: "The Batch Report cites Dr. Wen Zhao's telemetry findings as evidence the AGI-native shift is already paying off." },
  { source: 'batch_report', target: 'aisha_rahman', name: 'CITES', fact_type: 'media_coverage', episodes: [QUALITY_AUDIT],
    fact: 'The Batch Report also cites Aisha Rahman\'s conflicting audit findings, framing the 3.2x-vs-1.4x gap as the central open question.' },

  // Enterprise buyer cluster
  { source: 'hana_sato', target: 'ashford_retail', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Hana Sato serves as Chief Information Officer at Ashford Retail Group.' },
  { source: 'hana_sato', target: 'yc', name: 'COMMENTS_ON', fact_type: 'enterprise_procurement',
    fact: 'Hana Sato says enterprise procurement already assumes agent-augmented vendor teams, not headcount, when evaluating YC-backed startups.' },
  { source: 'enterprise_procurement_roundtable', target: 'agentforge', name: 'EVALUATES', fact_type: 'enterprise_procurement',
    fact: "The Enterprise Procurement Roundtable is evaluating AgentForge's tooling as a due-diligence signal for agent-native vendors." },
  { source: 'ashford_retail', target: 'cobalt_ledger', name: 'PARTNERS_WITH', fact_type: 'enterprise_procurement',
    fact: "Ashford Retail Group is piloting Cobalt Ledger's reconciliation agents in its finance back office." },

  // Community voice cluster
  { source: 'indie_builders_collective', target: 'gabe_torres', name: 'ADVOCATES_FOR', fact_type: 'community_sentiment',
    fact: "The Indie Builders Collective champions Gabe Torres as proof that solo agent-native builders don't need accelerator backing." },
  { source: 'winter2027_applicant_pool', target: 'agi_native_track', name: 'RAISES_CONCERN_ABOUT', fact_type: 'community_sentiment',
    fact: "The Winter 2027 Applicant Pool is already speculating about how the AGI-Native Track pilot will change YC's admission bar." },

  // Self loops (internal processes) - exercise self-loop rendering/grouping
  { source: 'yc', target: 'yc', name: 'UNDERGOES_STRATEGY_REVIEW', fact_type: 'internal_process',
    fact: "Y Combinator's partnership conducts an internal strategy review weighing a full AGI-native overhaul against the staged AGI-Native Track pilot." },
  { source: 'lp_advisory_council', target: 'lp_advisory_council', name: 'HOLDS_INTERNAL_RATIFICATION_VOTE', fact_type: 'internal_process',
    fact: 'The LP Advisory Council periodically holds an internal ratification vote among member LPs before endorsing a position on the AGI-Native Track.' }
]

const EDGE_GAP_SECONDS = 30
const VALID_AT_LEAD_SECONDS = 3600 // facts are "true" before they're captured in an episode

export const edges = EDGE_DEFS.map((def, idx) => {
  const sourceIdx = nodeIndex.get(def.source)
  const targetIdx = nodeIndex.get(def.target)
  const latestEndpointIdx = Math.max(sourceIdx, targetIdx)
  const createdOffset = latestEndpointIdx * NODE_SECONDS_STEP + EDGE_GAP_SECONDS + idx
  return {
    uuid: `edge_${idx}_${def.source}_${def.target}`,
    source_node_uuid: `node_${def.source}`,
    target_node_uuid: `node_${def.target}`,
    name: def.name,
    fact: def.fact,
    fact_type: def.fact_type,
    episodes: def.episodes || [BATCH_COMPOSITION_STUDY],
    created_at: ts(createdOffset),
    valid_at: ts(createdOffset - VALID_AT_LEAD_SECONDS)
  }
})

export default { nodes, edges }
