// Demo fixture: the Y Combinator / AGI-era project record returned by
// /api/graph/ontology/generate and /api/graph/project/:projectId.
//
// `status` here is a placeholder — src/demo/handlers/phase12.js overrides it
// based on the graphBuild clock job (see src/demo/clock.js) before returning
// this object to a consumer, per the ontology_generated -> graph_building ->
// graph_completed lifecycle MainView.vue expects (MainView.vue:258-266).

import { IDS, REQUIREMENT, ts } from './scenario.js'
import { DEFAULT_MODEL, DEFAULT_REASONING_EFFORT } from '../../constants/llmOptions.js'

export default {
  project_id: IDS.projectId,
  graph_id: IDS.graphId,
  status: 'ontology_generated',
  simulation_requirement: REQUIREMENT,
  ontology: {
    entity_types: [
      {
        name: 'AcceleratorProgram',
        description: 'An organization or internal program that selects, funds, and develops early-stage startups through a structured batch process.',
        attributes: [
          { name: 'batch_size', type: 'number', description: 'Approximate number of companies per batch or pilot cohort' },
          { name: 'focus_area', type: 'string', description: 'Primary selection or curriculum focus' }
        ],
        examples: ['Y Combinator', 'AGI-Native Track', 'Velocity Program']
      },
      {
        name: 'Partner',
        description: 'An individual holding a leadership, selection, or advisory role within an accelerator program.',
        attributes: [
          { name: 'role', type: 'string', description: 'Formal title or position' },
          { name: 'program', type: 'string', description: 'Accelerator program the partner belongs to' },
          { name: 'tenure', type: 'string', description: 'Time in current role, if known' }
        ],
        examples: ['Elena Voss (Group Partner)', 'Marcus Oyelaran (Managing Partner)', 'Priya Shenoy (Visiting Partner)']
      },
      {
        name: 'Founder',
        description: 'An individual who founded or co-founded a startup company, admitted to or evaluated by an accelerator program.',
        attributes: [
          { name: 'role', type: 'string', description: 'Founder title or function' },
          { name: 'company', type: 'string', description: 'Startup the founder leads' },
          { name: 'team_size', type: 'number', description: 'Approximate founding-team headcount, if known' }
        ],
        examples: ['Kai Nakamura (solo founder, Loomfield)', 'Sofia Marek (co-founder, Parallel Desk)']
      },
      {
        name: 'StartupCompany',
        description: 'An early-stage company built by one or more founders, typically admitted to or evaluated by an accelerator program.',
        attributes: [
          { name: 'industry', type: 'string', description: 'Primary product or market category' },
          { name: 'team_size', type: 'number', description: 'Approximate total headcount' },
          { name: 'agent_leverage_ratio', type: 'string', description: 'Ratio of agent output to human headcount, if disclosed' }
        ],
        examples: ['Loomfield', 'Parallel Desk', 'AgentForge']
      },
      {
        name: 'ResearchLab',
        description: 'A frontier AI research organization or its researchers producing capability, safety, or telemetry findings relevant to accelerator strategy.',
        attributes: [
          { name: 'focus_area', type: 'string', description: 'Primary research focus' },
          { name: 'employer', type: 'string', description: 'Organization the researcher belongs to, if an individual' }
        ],
        examples: ['Helios Research', 'Cascade AI Lab', 'Dr. Wen Zhao']
      },
      {
        name: 'InvestorLP',
        description: 'A limited partner, endowment, or investor providing capital to accelerator programs or tracking seed-market shifts.',
        attributes: [
          { name: 'investor_type', type: 'string', description: 'Category of investing entity' },
          { name: 'aum_usd', type: 'string', description: 'Approximate assets under management, if disclosed' }
        ],
        examples: ['Crestline University Endowment', 'Anchorpoint Ventures']
      }
    ],
    edge_types: [
      {
        name: 'FUNDS',
        description: 'A financial commitment where an accelerator program or investor provides capital to a startup, program, or fund.',
        attributes: [
          { name: 'amount_usd', type: 'number', description: 'Committed amount in US dollars, if disclosed' },
          { name: 'terms', type: 'string', description: 'Funding terms or tranche structure, if known' }
        ],
        examples: ['Y Combinator FUNDS AGI-Native Track', 'Crestline University Endowment FUNDS Y Combinator'],
        source_targets: [
          { source: 'AcceleratorProgram', target: 'StartupCompany' },
          { source: 'InvestorLP', target: 'AcceleratorProgram' }
        ]
      },
      {
        name: 'MENTORS',
        description: 'A partner or experienced founder provides direct guidance, coaching, or office hours to a founder.',
        attributes: [
          { name: 'focus_area', type: 'string', description: 'Subject of the mentorship' },
          { name: 'cadence', type: 'string', description: 'Frequency of contact, if known' }
        ],
        examples: ['Elena Voss MENTORS Kai Nakamura', 'Leo Martins MENTORS Gabe Torres'],
        source_targets: [
          { source: 'Partner', target: 'Founder' },
          { source: 'Founder', target: 'Founder' }
        ]
      },
      {
        name: 'BUILDS_WITH',
        description: 'A startup builds product, infrastructure, or evaluation tooling in direct collaboration with another startup or research lab.',
        attributes: [
          { name: 'stack_component', type: 'string', description: 'Shared tooling or infrastructure layer' },
          { name: 'dependency_level', type: 'string', description: 'How load-bearing the collaboration is, if known' }
        ],
        examples: ['Loomfield BUILDS_WITH AgentForge', 'Evalio BUILDS_WITH Helios Research'],
        source_targets: [
          { source: 'StartupCompany', target: 'StartupCompany' },
          { source: 'StartupCompany', target: 'ResearchLab' }
        ]
      },
      {
        name: 'PUBLISHES',
        description: 'A research lab releases a study, dataset, or capability benchmark relevant to accelerator selection strategy.',
        attributes: [
          { name: 'title', type: 'string', description: 'Title or subject of the publication' },
          { name: 'publish_date', type: 'string', description: 'Publication date, if known' }
        ],
        examples: ['Helios Research PUBLISHES the agent leverage telemetry study', 'Cascade AI Lab PUBLISHES the post-batch quality audit'],
        source_targets: [
          { source: 'ResearchLab', target: 'AcceleratorProgram' }
        ]
      },
      {
        name: 'COMPETES_WITH',
        description: 'One accelerator program vies with another for applicant deal flow, talent, or positioning.',
        attributes: [
          { name: 'basis_of_competition', type: 'string', description: 'What the two programs are competing over' }
        ],
        examples: ['Velocity Program COMPETES_WITH Y Combinator'],
        source_targets: [
          { source: 'AcceleratorProgram', target: 'AcceleratorProgram' }
        ]
      },
      {
        name: 'DEBATES_WITH',
        description: 'An individual or organization publicly disputes evidence, selection criteria, or the pace of the AGI-native transition with a partner.',
        attributes: [
          { name: 'topic', type: 'string', description: 'Subject of the dispute' },
          { name: 'stance', type: 'string', description: 'Position taken, if known' }
        ],
        examples: ['Aisha Rahman DEBATES_WITH Elena Voss', 'Rachel Adeyemi DEBATES_WITH Elena Voss'],
        source_targets: [
          { source: 'ResearchLab', target: 'Partner' },
          { source: 'InvestorLP', target: 'Partner' }
        ]
      }
    ]
  },
  llm_model: DEFAULT_MODEL,
  llm_reasoning_effort: DEFAULT_REASONING_EFFORT,
  created_at: ts(0)
}
