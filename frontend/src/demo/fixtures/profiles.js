// Demo fixture: the 16 simulation agent personas generated during Step 2
// environment setup. Consumed by src/components/Step2EnvSetup.vue via
// GET /api/simulation/:id/profiles/realtime (profile.username/name/
// profession/bio/interested_topics are rendered directly; profile.entity_type
// feeds the "entity types found" log line and src/demo/fixtures/simConfig.js
// agent_configs, which is index-aligned with this array by agent_id).
//
// Field names mirror the graph node vocabulary (see graph.js) but a handful
// of personas stand in for a broader community/segment voice rather than a
// single named graph node (e.g. the Indie Builders Collective moderator).

export default [
  {
    username: 'Elena Voss',
    name: 'elenavoss',
    profession: 'Group Partner, Y Combinator',
    bio: 'Leads the AGI-Native Track and is the pragmatic champion of a staged, reversible pilot over a full batch-model overhaul. Weighs founder upside against brand and oversight risk.',
    interested_topics: ['AGI-native selection', 'pilot design', 'agent leverage', 'batch strategy'],
    entity_type: 'Partner'
  },
  {
    username: 'Marcus Oyelaran',
    name: 'marcus_oyelaran_yc',
    profession: 'Managing Partner, Y Combinator',
    bio: "Protects YC's brand across four decades of accumulated trust and demands reversibility and guardrails before any AGI-native expansion proceeds.",
    interested_topics: ['brand risk', 'reversibility', 'governance', 'pause triggers'],
    entity_type: 'Partner'
  },
  {
    username: 'Priya Shenoy',
    name: 'priya_shenoy_yc',
    profession: 'Visiting Partner, Y Combinator',
    bio: 'A former frontier-lab researcher who translates capability curves into concrete batch-strategy recommendations for the partnership.',
    interested_topics: ['capability curves', 'curriculum design', 'frontier research', 'batch strategy'],
    entity_type: 'Partner'
  },
  {
    username: 'Kai Nakamura',
    name: 'kai_ships',
    profession: 'Solo Founder, Loomfield',
    bio: 'Runs a 40-agent fleet to $2.1M ARR entirely alone. The clearest live example of the agent-native applicant archetype YC is debating whether to prioritize.',
    interested_topics: ['agent fleets', 'solo founder economics', 'agent leverage ratio', 'vertical SaaS'],
    entity_type: 'Founder'
  },
  {
    username: 'Sofia Marek',
    name: 'sofia_marek_pd',
    profession: 'Co-founder, Parallel Desk',
    bio: 'Co-founded a traditional nine-person B2B SaaS team and feels the selection ground shifting as agent-native applicants dominate the conversation.',
    interested_topics: ['traditional team building', 'hiring', 'B2B SaaS', 'selection criteria fairness'],
    entity_type: 'Founder'
  },
  {
    username: 'Dr. Wen Zhao',
    name: 'wenzhao_research',
    profession: 'Researcher, Helios Research',
    bio: 'Publishes capability-curve and telemetry data showing agent-native teams shipped 3.2x more weekly releases in their first 12 weeks.',
    interested_topics: ['capability curves', 'telemetry studies', 'agent-native velocity', 'frontier research'],
    entity_type: 'ResearchLab'
  },
  {
    username: 'Tomas Lindqvist',
    name: 'tomas_agentforge',
    profession: 'CTO, AgentForge',
    bio: 'Builds the agent-infrastructure tooling underpinning several other AGI-native applicants, including Loomfield and Evalio.',
    interested_topics: ['agent infrastructure', 'orchestration tooling', 'developer platforms'],
    entity_type: 'Founder'
  },
  {
    username: 'Rachel Adeyemi',
    name: 'radeyemi_lp',
    profession: 'Limited Partner, Crestline University Endowment',
    bio: "Skeptical that accelerator returns hold up in the AGI era if batch composition shifts too far from proven team structures.",
    interested_topics: ['LP returns', 'endowment risk', 'fund performance', 'batch composition'],
    entity_type: 'InvestorLP'
  },
  {
    username: 'Dev Kapoor',
    name: 'devkapoor_velocity',
    profession: 'Partner, Velocity Program',
    bio: "Publicly mocks YC's caution and runs an all-in AGI-native track of his own at a rival accelerator.",
    interested_topics: ['rival accelerators', 'AGI-native tracks', 'applicant deal flow', 'competitive positioning'],
    entity_type: 'AcceleratorProgram'
  },
  {
    username: 'Maya Chen',
    name: 'batchreport_maya',
    profession: 'Journalist, The Batch Report',
    bio: "Broke the leaked-memo story that YC is drafting an AGI-Native Track, driving the discourse from day one.",
    interested_topics: ['accelerator reporting', 'leaked memos', 'startup media', 'AGI-native coverage'],
    entity_type: 'MediaOutlet'
  },
  {
    username: 'Jonah Price',
    name: 'jonahprice_evalio',
    profession: 'Founder, Evalio',
    bio: 'A PhD dropout building agent-evals tooling full time; his benchmarks feed directly into partner interview criteria.',
    interested_topics: ['agent evaluation', 'benchmarking', 'taste and judgment', 'PhD dropout life'],
    entity_type: 'Founder'
  },
  {
    username: 'Aisha Rahman',
    name: 'aisha_safety',
    profession: 'Alignment & Safety Researcher, Cascade AI Lab',
    bio: 'Argues selection criteria must weigh oversight competence, citing 2.4x more critical production incidents in agent-heavy teams without senior oversight.',
    interested_topics: ['AI safety', 'oversight competence', 'incident rates', 'selection criteria'],
    entity_type: 'ResearchLab'
  },
  {
    username: 'Leo Martins',
    name: 'leomartins_2x',
    profession: 'Founder, Quiet Systems',
    bio: 'A second-time founder who exited in 2024 and now builds agent-native; mentors first-timers navigating the shift to tiny, agent-leveraged teams.',
    interested_topics: ['repeat founders', 'agent-native ops', 'mentorship', 'team structure'],
    entity_type: 'Founder'
  },
  {
    username: 'Hana Sato',
    name: 'hanasato_cio',
    profession: 'Chief Information Officer, Ashford Retail Group',
    bio: 'Represents the enterprise demand side: procurement already assumes agent-augmented vendor teams, not headcount.',
    interested_topics: ['enterprise procurement', 'vendor evaluation', 'agent-augmented teams'],
    entity_type: 'EnterpriseBuyer'
  },
  {
    username: 'Gabe Torres',
    name: 'gabe_indiehacks',
    profession: 'Indie Founder, Fieldnote',
    bio: 'Built a viral consumer agent app solo and is publicly skeptical that accelerators add value for agent-native solo builders.',
    interested_topics: ['indie hacking', 'consumer agent apps', 'distribution instinct', 'accelerator skepticism'],
    entity_type: 'Founder'
  },
  {
    username: 'Nadia Petrova',
    name: 'nadiap_seed',
    profession: 'Early-stage VC Analyst',
    bio: 'Tracks how agent leverage is already reshaping seed-market valuations and check sizes across the industry.',
    interested_topics: ['seed-stage valuations', 'venture analysis', 'agent leverage', 'market shifts'],
    entity_type: 'InvestorLP'
  }
]
