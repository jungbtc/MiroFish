// Demo fixture: the 16 simulation agent personas generated during Step 2
// environment setup. Consumed by src/components/Step2EnvSetup.vue via
// GET /api/simulation/:id/profiles/realtime (profile.username/name/
// profession/bio/interested_topics are rendered directly; profile.entity_type
// feeds the "entity types found" log line and src/demo/fixtures/simConfig.js
// agent_configs, which is index-aligned with this array by agent_id).
//
// Field names mirror the graph node vocabulary (see graph.js) but a handful
// of personas stand in for a broader community/segment voice rather than a
// single named graph node (e.g. the Northstar Loyalists moderator).

export default [
  {
    username: 'Dana Whitfield',
    name: 'dana_whitfield_ceo',
    profession: 'Chief Executive Officer, Northstar Appliances',
    bio: 'Steers Northstar Appliances through the restructuring decision, weighing lender pressure against workforce and brand risk. Publicly favors a measured, reversible approach.',
    interested_topics: ['restructuring strategy', 'stakeholder trust', 'liquidity management', 'brand reputation'],
    entity_type: 'Executive'
  },
  {
    username: 'Marcus Lee',
    name: 'marcus_lee_cfo',
    profession: 'Chief Financial Officer, Northstar Appliances',
    bio: 'Modeled the 11-week liquidity runway and leads covenant negotiations with Meridian Lending Group, focused on preserving cash without triggering default.',
    interested_topics: ['liquidity runway', 'covenant compliance', 'cash flow forecasting'],
    entity_type: 'Executive'
  },
  {
    username: 'Priya Nandakumar',
    name: 'priya_toledo_ops',
    profession: 'Plant Manager, Toledo Assembly Plant',
    bio: 'Runs day-to-day operations at the Toledo plant and has watched morale erode after two rounds of layoff rumors. Prefers a pilot over abrupt closure.',
    interested_topics: ['plant operations', 'worker morale', 'production continuity'],
    entity_type: 'Executive'
  },
  {
    username: 'Robert Hayes',
    name: 'robert_macon_ops',
    profession: 'Plant Manager, Macon Assembly Plant',
    bio: 'Oversees the Macon laundry-appliance plant and argues a phased approach avoids losing skilled line workers to competitors.',
    interested_topics: ['skilled labor retention', 'phased restructuring', 'plant efficiency'],
    entity_type: 'Executive'
  },
  {
    username: 'Grace Liu',
    name: 'grace_liu_comms',
    profession: 'VP Corporate Communications, Northstar Appliances',
    bio: 'Manages external messaging to retail partners, media, and employees during the restructuring decision window.',
    interested_topics: ['crisis communications', 'stakeholder messaging', 'media relations'],
    entity_type: 'Executive'
  },
  {
    username: 'Elena Cho',
    name: 'elena_cho_supply',
    profession: 'VP Supply Chain, Northstar Appliances',
    bio: 'Coordinates directly with Karlin Components and other suppliers to protect critical payment terms during any pilot program.',
    interested_topics: ['supplier relations', 'payment protection', 'supply chain risk'],
    entity_type: 'Executive'
  },
  {
    username: 'Denise Ruiz',
    name: 'denise_ruiz_uaw',
    profession: 'Chief Shop Steward, UAW Local 1180',
    bio: 'Leads union negotiations for Toledo workers, pushing for a firm sunset date on any pilot plus consultation rights before permanent closures.',
    interested_topics: ['job security', 'union rights', 'consultation process'],
    entity_type: 'LaborUnion'
  },
  {
    username: 'Jordan Ellis',
    name: 'jordan_ellis_eng',
    profession: 'Former Process Engineer, Toledo Plant (laid off)',
    bio: 'Laid off in a prior cost round, now publicly critical of unclear communication and worried the same pattern will repeat with this decision.',
    interested_topics: ['layoff communication', 'worker transparency', 'severance fairness'],
    entity_type: 'LaborUnion'
  },
  {
    username: 'Tom Reyes',
    name: 'tom_reyes_karlin',
    profession: 'Chief Financial Officer, Karlin Components',
    bio: "Warns that delayed approvals and unclear ownership could cut Northstar's expected cash-burn savings from 18% to as low as 6%.",
    interested_topics: ['payment terms', 'supplier risk', 'cash-burn benchmarks'],
    entity_type: 'Supplier'
  },
  {
    username: 'Sarah Kwan',
    name: 'sarah_kwan_meridian',
    profession: 'Senior Credit Analyst, Meridian Lending Group',
    bio: 'Drafted the covenant terms tying continued credit access to weekly liquidity reporting and critical-supplier payment protection.',
    interested_topics: ['covenant compliance', 'liquidity reporting', 'credit risk'],
    entity_type: 'Lender'
  },
  {
    username: 'Alicia Brooks',
    name: 'alicia_brooks_homeplex',
    profession: 'VP Merchandising, HomePlex Retail Corp',
    bio: "Requests a written supply-continuity plan from Northstar before committing to next season's purchase orders.",
    interested_topics: ['supply continuity', 'retail purchase orders', 'vendor risk'],
    entity_type: 'RetailPartner'
  },
  {
    username: 'Sam Okafor',
    name: 'sam_okafor_reports',
    profession: 'Industry Journalist, Midwest Business Journal',
    bio: 'Covers the restructuring decision and the supplier survey findings on cash-burn impact for a regional business audience.',
    interested_topics: ['industry reporting', 'restructuring coverage', 'supplier surveys'],
    entity_type: 'MediaOutlet'
  },
  {
    username: 'Northstar Loyalists Community',
    name: 'northstar_loyalists_mod',
    profession: 'Community Moderator, Northstar Loyalists',
    bio: 'Moderates a 40,000-member brand community and tracks warranty and service-continuity questions from long-time customers.',
    interested_topics: ['warranty coverage', 'service continuity', 'brand trust'],
    entity_type: 'CustomerSegment'
  },
  {
    username: 'Renee Castillo',
    name: 'budget_conscious_renee',
    profession: 'Consumer Advocate, Price-Sensitive Households',
    bio: 'Speaks for budget-conscious buyers worried that restructuring costs will be passed on through price increases.',
    interested_topics: ['appliance pricing', 'household budgets', 'consumer advocacy'],
    entity_type: 'CustomerSegment'
  },
  {
    username: 'Marcus Ito',
    name: 'fixit_marcus',
    profession: 'Independent Appliance Repair Technician',
    bio: 'Active in the Appliance Repair Community Forum, tracking parts-supply risk tied to the restructuring decision.',
    interested_topics: ['parts availability', 'repair community', 'service continuity'],
    entity_type: 'CustomerSegment'
  },
  {
    username: 'Toledo Community Advocates',
    name: 'toledo_civic_voice',
    profession: 'Civic Organizer, Toledo Community Advocates',
    bio: 'Organizes public comment sessions in support of Toledo Assembly Plant workers ahead of any closure announcement.',
    interested_topics: ['local jobs', 'civic advocacy', 'plant closures'],
    entity_type: 'CustomerSegment'
  }
]
