// Demo fixture: the Northstar Appliances project record returned by
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
        name: 'Company',
        description: 'An organization operating as a business entity in the appliance manufacturing or retail supply chain.',
        attributes: [
          { name: 'industry', type: 'string', description: 'Primary business sector' },
          { name: 'headquarters', type: 'string', description: 'Primary corporate location' },
          { name: 'employees', type: 'number', description: 'Approximate total workforce size' }
        ],
        examples: ['Northstar Appliances Inc.', 'Northstar Appliances']
      },
      {
        name: 'Executive',
        description: 'An individual holding a leadership, management, or governance role within Northstar Appliances or a partner organization.',
        attributes: [
          { name: 'role', type: 'string', description: 'Formal title or position' },
          { name: 'employer', type: 'string', description: 'Organization the executive belongs to' },
          { name: 'tenure', type: 'string', description: 'Time in current role, if known' }
        ],
        examples: ['Dana Whitfield (CEO)', 'Marcus Lee (CFO)', 'Priya Nandakumar (Plant Manager)']
      },
      {
        name: 'Lender',
        description: 'A financial institution or syndicate member providing secured credit to Northstar Appliances.',
        attributes: [
          { name: 'facility_size', type: 'string', description: 'Size of the credit facility or syndicate share' },
          { name: 'role', type: 'string', description: 'Role within the lending relationship' }
        ],
        examples: ['Meridian Lending Group', 'Cascade Capital']
      },
      {
        name: 'Supplier',
        description: "A vendor providing components, materials, or subassemblies to Northstar Appliances' manufacturing plants.",
        attributes: [
          { name: 'role', type: 'string', description: 'Category of goods supplied' },
          { name: 'dependency', type: 'string', description: 'Approximate share of volume supplied, if known' }
        ],
        examples: ['Karlin Components', 'Ironclad Steel Supply', 'Vantage Plastics Group']
      },
      {
        name: 'LaborUnion',
        description: "A union body, negotiating committee, or worker representative involved in labor relations at Northstar Appliances' plants.",
        attributes: [
          { name: 'role', type: 'string', description: 'Union function or position' },
          { name: 'location', type: 'string', description: 'Associated plant location, if applicable' },
          { name: 'members', type: 'number', description: 'Approximate membership size, if known' }
        ],
        examples: ['United Appliance Workers Local 1180', 'United Appliance Workers Local 2214']
      },
      {
        name: 'Plant',
        description: 'A manufacturing or distribution facility operated by Northstar Appliances.',
        attributes: [
          { name: 'location', type: 'string', description: 'City and state of the facility' },
          { name: 'workforce', type: 'number', description: 'Approximate number of employees at the facility' },
          { name: 'product_line', type: 'string', description: 'Primary products manufactured or handled' }
        ],
        examples: ['Northstar Toledo Assembly Plant', 'Northstar Macon Assembly Plant']
      }
    ],
    edge_types: [
      {
        name: 'OWES_TO',
        description: 'A financial obligation where one entity owes money, credit repayment, or outstanding invoices to another.',
        attributes: [
          { name: 'amount_usd', type: 'number', description: 'Outstanding balance in US dollars, if disclosed' },
          { name: 'due_date', type: 'string', description: 'Repayment or covenant deadline, if known' }
        ],
        examples: ['Northstar Appliances OWES_TO Meridian Lending Group', 'Northstar Appliances OWES_TO Karlin Components'],
        source_targets: [
          { source: 'Company', target: 'Lender' },
          { source: 'Company', target: 'Supplier' }
        ]
      },
      {
        name: 'SUPPLIES_TO',
        description: 'Indicates a supplier delivers components or materials to a manufacturing plant or company.',
        attributes: [
          { name: 'component_category', type: 'string', description: 'Type of component or material supplied' },
          { name: 'payment_terms', type: 'string', description: 'Standard payment terms, if disclosed' }
        ],
        examples: ['Karlin Components SUPPLIES_TO Northstar Appliances', 'Ironclad Steel Supply SUPPLIES_TO Northstar Toledo Assembly Plant'],
        source_targets: [
          { source: 'Supplier', target: 'Company' },
          { source: 'Supplier', target: 'Plant' }
        ]
      },
      {
        name: 'OPERATES',
        description: 'Indicates a company or executive runs or manages a manufacturing or distribution facility.',
        attributes: [
          { name: 'since', type: 'string', description: 'Date operations began, if known' }
        ],
        examples: ['Northstar Appliances OPERATES Northstar Toledo Assembly Plant', 'Priya Nandakumar OPERATES Northstar Toledo Assembly Plant'],
        source_targets: [
          { source: 'Company', target: 'Plant' },
          { source: 'Executive', target: 'Plant' }
        ]
      },
      {
        name: 'REPRESENTS',
        description: 'Indicates a labor union or union representative advocates for workers at a specific facility.',
        attributes: [
          { name: 'members_represented', type: 'number', description: 'Approximate number of workers represented, if known' }
        ],
        examples: ['United Appliance Workers Local 1180 REPRESENTS Northstar Toledo Assembly Plant'],
        source_targets: [
          { source: 'LaborUnion', target: 'Plant' }
        ]
      },
      {
        name: 'LEADS',
        description: 'Indicates an executive holds a leadership or governance role over a company.',
        attributes: [
          { name: 'title', type: 'string', description: 'Formal leadership title' }
        ],
        examples: ['Dana Whitfield LEADS Northstar Appliances'],
        source_targets: [
          { source: 'Executive', target: 'Company' }
        ]
      },
      {
        name: 'NEGOTIATES_WITH',
        description: 'Indicates a labor union or worker representative is in active negotiation with company leadership over restructuring terms.',
        attributes: [
          { name: 'topic', type: 'string', description: 'Subject of negotiation' },
          { name: 'status', type: 'string', description: 'Current negotiation status, if known' }
        ],
        examples: ['United Appliance Workers Local 1180 NEGOTIATES_WITH Northstar Appliances'],
        source_targets: [
          { source: 'LaborUnion', target: 'Company' }
        ]
      }
    ]
  },
  llm_model: DEFAULT_MODEL,
  llm_reasoning_effort: DEFAULT_REASONING_EFFORT,
  created_at: ts(0)
}
