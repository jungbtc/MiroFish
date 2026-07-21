// Demo fixture: the Northstar Appliances knowledge graph returned by
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
// first, periphery later": the company, its executives and immediate
// lenders/plants surface early; suppliers, labor, retail, customer and
// media voices fill in afterward.

import { ts } from './scenario.js'

const LIQUIDITY_FILING = 'northstar_liquidity_filing.pdf'
const LENDER_LETTER = 'lender_letter.pdf'
const RESTRUCTURING_BENCHMARK = 'restructuring_benchmark.md'

// --- Node roster --------------------------------------------------------
// Index in this array determines created_at (ts(idx * 20)) and therefore
// reveal order.
const NODE_DEFS = [
  // Company
  { id: 'northstar', name: 'Northstar Appliances Inc.', type: 'Company',
    attributes: { industry: 'Home & Kitchen Appliances', headquarters: 'Toledo, Ohio', founded: '1962', employees: '4,800' },
    summary: 'Mid-market home appliance manufacturer with roughly 11 weeks of operating cash remaining, weighing an immediate company-wide restructuring against a staged, reversible pilot.' },

  // Executives
  { id: 'dana_whitfield', name: 'Dana Whitfield', type: 'Executive',
    attributes: { role: 'Chief Executive Officer', employer: 'Northstar Appliances', tenure: '6 years' },
    summary: 'CEO driving the choice between an immediate restructuring and a staged pilot; publicly cautious about morale and brand damage from abrupt closures.' },
  { id: 'marcus_lee', name: 'Marcus Lee', type: 'Executive',
    attributes: { role: 'Chief Financial Officer', employer: 'Northstar Appliances', tenure: '3 years' },
    summary: 'CFO who modeled the 11-week liquidity runway and is the primary liaison to Meridian Lending Group on covenant terms.' },
  { id: 'priya_nandakumar', name: 'Priya Nandakumar', type: 'Executive',
    attributes: { role: 'Plant Manager', employer: 'Northstar Appliances', location: 'Toledo, OH' },
    summary: 'Manages the Toledo assembly plant and has watched morale erode after two rounds of layoff rumors; prefers a pilot over abrupt closure.' },
  { id: 'robert_hayes', name: 'Robert Hayes', type: 'Executive',
    attributes: { role: 'Plant Manager', employer: 'Northstar Appliances', location: 'Macon, GA' },
    summary: 'Manages the Macon assembly plant; supports a phased approach that avoids losing skilled line workers to competitors.' },
  { id: 'elena_cho', name: 'Elena Cho', type: 'Executive',
    attributes: { role: 'VP, Supply Chain', employer: 'Northstar Appliances' },
    summary: 'Coordinates with Karlin Components and other suppliers on payment protections during the proposed pilot.' },
  { id: 'grace_liu', name: 'Grace Liu', type: 'Executive',
    attributes: { role: 'VP, Corporate Communications', employer: 'Northstar Appliances' },
    summary: 'Manages external messaging to retail partners, media, and the workforce during the decision window.' },
  { id: 'board_of_directors', name: 'Northstar Appliances Board of Directors', type: 'Executive',
    attributes: { role: 'Governance Body', size: '7 members' },
    summary: 'Oversight board weighing fiduciary duty to lenders against reputational and workforce risk of an abrupt restructuring.' },

  // Lenders
  { id: 'meridian', name: 'Meridian Lending Group', type: 'Lender',
    attributes: { role: 'Secured Lender Group', facility_size: '$140M revolving credit facility' },
    summary: 'Secured lender group that will support a reversible pilot only if Northstar adopts weekly liquidity reporting and protects critical-supplier payments.' },
  { id: 'sarah_kwan', name: 'Sarah Kwan', type: 'Lender',
    attributes: { role: 'Senior Credit Analyst', employer: 'Meridian Lending Group' },
    summary: 'Analyst who drafted the covenant terms tying continued credit access to weekly liquidity disclosure.' },
  { id: 'meridian_credit_committee', name: 'Meridian Credit Committee', type: 'Lender',
    attributes: { role: 'Internal Approval Body', employer: 'Meridian Lending Group' },
    summary: 'Internal committee that must ratify any forbearance or covenant waiver tied to the pilot proposal.' },
  { id: 'cascade_capital', name: 'Cascade Capital', type: 'Lender',
    attributes: { role: 'Syndicate Participant', share: '22%' },
    summary: "Minority syndicate lender pushing for a stricter reporting cadence than Meridian's base proposal." },
  { id: 'vault_street_partners', name: 'Vault Street Partners', type: 'Lender',
    attributes: { role: 'Syndicate Participant', share: '15%' },
    summary: "Syndicate lender generally aligned with Meridian's reversible-pilot recommendation." },

  // Suppliers
  { id: 'karlin_components', name: 'Karlin Components', type: 'Supplier',
    attributes: { role: 'Tier-1 Electronics Supplier', dependency: '38% of control-board volume' },
    summary: "Critical electronics supplier whose payment terms are central to the lender's critical-supplier protection condition." },
  { id: 'tom_reyes', name: 'Tom Reyes', type: 'Supplier',
    attributes: { role: 'Chief Financial Officer', employer: 'Karlin Components' },
    summary: 'Supplier-side CFO warning that delayed approvals and unclear ownership could cut expected cash-burn savings from 18% to as low as 6%.' },
  { id: 'ironclad_steel', name: 'Ironclad Steel Supply', type: 'Supplier',
    attributes: { role: 'Raw Materials Supplier' },
    summary: 'Steel supplier to both Toledo and Macon plants; requested clarity on purchase-order continuity during any pilot.' },
  { id: 'precision_fasteners', name: 'Precision Fasteners Inc', type: 'Supplier',
    attributes: { role: 'Component Supplier' },
    summary: 'Smaller supplier flagged as vulnerable to payment delays if restructuring proceeds without protections.' },
  { id: 'vantage_plastics', name: 'Vantage Plastics Group', type: 'Supplier',
    attributes: { role: 'Molded Components Supplier' },
    summary: 'Supplies molded housings; participated in the supplier survey on restructuring cash-burn impact.' },
  { id: 'bellwood_motors', name: 'Bellwood Motors Corp', type: 'Supplier',
    attributes: { role: 'Motor Components Supplier' },
    summary: 'Supplies compressor motors; flagged approval-process delays as a recurring friction point in the supplier survey.' },
  { id: 'summit_electronics', name: 'Summit Electronics Components', type: 'Supplier',
    attributes: { role: 'Electronics Supplier' },
    summary: "Secondary electronics supplier being evaluated as a hedge against Karlin Components' concentration risk." },

  // Labor
  { id: 'uaw_local_1180', name: 'United Appliance Workers Local 1180', type: 'LaborUnion',
    attributes: { role: 'Local Union Chapter', location: 'Toledo, OH', members: '1,300' },
    summary: 'Toledo local representing assembly-line workers; supports the pilot if it includes a firm sunset date.' },
  { id: 'uaw_local_2214', name: 'United Appliance Workers Local 2214', type: 'LaborUnion',
    attributes: { role: 'Local Union Chapter', location: 'Macon, GA', members: '980' },
    summary: 'Macon local pressing for consultation rights before any permanent plant-closure decision.' },
  { id: 'uaw_international', name: 'United Appliance Workers International', type: 'LaborUnion',
    attributes: { role: 'National Union Body' },
    summary: 'National union office confirming the labor agreement permits a time-limited pilot but mandates consultation before permanent closures.' },
  { id: 'denise_ruiz', name: 'Denise Ruiz', type: 'LaborUnion',
    attributes: { role: 'Chief Shop Steward', employer: 'United Appliance Workers Local 1180' },
    summary: 'Lead negotiator communicating union conditions for accepting a reversible pilot over immediate restructuring.' },
  { id: 'jordan_ellis', name: 'Jordan Ellis', type: 'LaborUnion',
    attributes: { role: 'Former Process Engineer', location: 'Toledo, OH', status: 'Laid off in a prior cost round' },
    summary: 'Previously laid-off engineer whose public account of unclear communication is cited in coverage of the restructuring decision.' },
  { id: 'uaw_bargaining_committee', name: 'UAW Joint Bargaining Committee', type: 'LaborUnion',
    attributes: { role: 'Cross-local Negotiating Body' },
    summary: 'Joint committee coordinating Toledo and Macon local positions ahead of management’s decision.' },

  // Plants
  { id: 'toledo_plant', name: 'Northstar Toledo Assembly Plant', type: 'Plant',
    attributes: { location: 'Toledo, OH', workforce: '1,450', product_line: 'Refrigeration' },
    summary: 'Primary refrigeration assembly plant; a proposed pilot site for reversible restructuring measures.' },
  { id: 'macon_plant', name: 'Northstar Macon Assembly Plant', type: 'Plant',
    attributes: { location: 'Macon, GA', workforce: '1,120', product_line: 'Laundry appliances' },
    summary: 'Laundry appliance assembly plant; plant management supports a phased pilot to preserve skilled labor.' },
  { id: 'georgia_distribution_center', name: 'Northstar Georgia Distribution Center', type: 'Plant',
    attributes: { location: 'Macon, GA', workforce: '240' },
    summary: "Regional distribution hub whose staffing is indirectly affected by the Macon plant's restructuring scenario." },

  // Retail partners
  { id: 'homeplex', name: 'HomePlex Retail Corp', type: 'RetailPartner',
    attributes: { role: 'National Retail Partner', shelf_share: "27% of Northstar's unit sales" },
    summary: 'Largest retail partner monitoring supply-continuity risk from the restructuring decision.' },
  { id: 'alicia_brooks', name: 'Alicia Brooks', type: 'RetailPartner',
    attributes: { role: 'VP, Merchandising', employer: 'HomePlex Retail Corp' },
    summary: "Retail executive requesting a written continuity plan before committing to next season's purchase orders." },
  { id: 'bigbox_home', name: 'BigBox Home Retail', type: 'RetailPartner',
    attributes: { role: 'Secondary Retail Partner' },
    summary: "Secondary retail channel watching Northstar's decision as a signal for shifting orders to competitors." },
  { id: 'regional_hardware_coop', name: 'Regional Hardware Co-op', type: 'RetailPartner',
    attributes: { role: 'Independent Dealer Network' },
    summary: 'Network of independent dealers concerned about parts availability during any restructuring pilot.' },

  // Customer segments / community voices
  { id: 'northstar_loyalists', name: 'Northstar Loyalists Community', type: 'CustomerSegment',
    attributes: { role: 'Brand Community', size_estimate: '~40,000 members' },
    summary: 'Long-time customer community voicing concern over warranty and service continuity amid restructuring speculation.' },
  { id: 'price_sensitive_households', name: 'Price-Sensitive Households Segment', type: 'CustomerSegment',
    attributes: { role: 'Demographic Segment' },
    summary: 'Budget-conscious buyer segment sensitive to any price increases used to fund restructuring costs.' },
  { id: 'appliance_repair_community', name: 'Appliance Repair Community Forum', type: 'CustomerSegment',
    attributes: { role: 'Online Community' },
    summary: 'Independent repair technicians discussing parts-supply risk tied to the restructuring decision.' },
  { id: 'toledo_community_advocates', name: 'Toledo Community Advocates', type: 'CustomerSegment',
    attributes: { role: 'Local Civic Group', location: 'Toledo, OH' },
    summary: 'Local civic group organizing public comment ahead of any permanent plant-closure announcement.' },

  // Media
  { id: 'midwest_business_journal', name: 'Midwest Business Journal', type: 'MediaOutlet',
    attributes: { role: 'Regional Business Publication' },
    summary: "Regional outlet that first reported Northstar's roughly 11-week liquidity runway estimate." },
  { id: 'sam_okafor', name: 'Sam Okafor', type: 'MediaOutlet',
    attributes: { role: 'Industry Journalist', employer: 'Midwest Business Journal' },
    summary: 'Journalist covering the restructuring decision and the supplier survey findings.' },
  { id: 'appliance_trade_press', name: 'Appliance Trade Press', type: 'MediaOutlet',
    attributes: { role: 'Trade Publication' },
    summary: 'Trade publication that published the industry benchmark citing an 18% cash-burn reduction from staged programs.' },
  { id: 'trade_wire_newsletter', name: 'Trade Wire Newsletter', type: 'MediaOutlet',
    attributes: { role: 'Industry Newsletter' },
    summary: 'Newsletter tracking lender and union reactions across the appliance manufacturing sector.' },
  { id: 'local_toledo_news12', name: 'Local Toledo News 12', type: 'MediaOutlet',
    attributes: { role: 'Local Broadcast News' },
    summary: 'Local broadcaster covering community reaction in Toledo to potential plant restructuring.' }
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
  // Financial / lender cluster
  { source: 'northstar', target: 'meridian', name: 'OWES_TO', fact_type: 'financial_obligation', episodes: [LENDER_LETTER],
    fact: 'Northstar Appliances owes approximately $140 million under its revolving credit facility with Meridian Lending Group, which covers only about 11 weeks of operating cash.' },
  { source: 'meridian', target: 'northstar', name: 'IMPOSES_CONDITIONS_ON', fact_type: 'covenant_condition', episodes: [LENDER_LETTER],
    fact: 'Meridian Lending Group will support a reversible pilot only if Northstar Appliances adopts weekly liquidity reporting and protects critical-supplier payments.' },
  { source: 'northstar', target: 'karlin_components', name: 'OWES_TO', fact_type: 'financial_obligation', episodes: [LENDER_LETTER],
    fact: 'Northstar Appliances owes Karlin Components outstanding invoices that Meridian Lending Group wants protected from delay during any pilot.' },
  { source: 'sarah_kwan', target: 'meridian', name: 'MEMBER_OF', fact_type: 'membership', episodes: [LENDER_LETTER],
    fact: 'Sarah Kwan is a senior credit analyst at Meridian Lending Group.' },
  { source: 'meridian_credit_committee', target: 'meridian', name: 'MEMBER_OF', fact_type: 'membership', episodes: [LENDER_LETTER],
    fact: 'The Meridian Credit Committee is the internal approval body within Meridian Lending Group responsible for ratifying covenant waivers.' },
  { source: 'cascade_capital', target: 'meridian', name: 'MEMBER_OF', fact_type: 'membership', episodes: [LENDER_LETTER],
    fact: 'Cascade Capital holds a 22% share of the Meridian-led lending syndicate backing Northstar Appliances.' },
  { source: 'vault_street_partners', target: 'meridian', name: 'MEMBER_OF', fact_type: 'membership', episodes: [LENDER_LETTER],
    fact: 'Vault Street Partners holds a 15% share of the Meridian-led lending syndicate.' },
  { source: 'sarah_kwan', target: 'northstar', name: 'DRAFTS_TERMS_FOR', fact_type: 'covenant_condition', episodes: [LENDER_LETTER],
    fact: 'Sarah Kwan drafted the covenant terms tying continued credit access to weekly liquidity disclosure for Northstar Appliances.' },
  { source: 'cascade_capital', target: 'northstar', name: 'RAISES_CONCERN_ABOUT', fact_type: 'covenant_condition', episodes: [LENDER_LETTER],
    fact: "Cascade Capital is pushing for a stricter weekly reporting cadence than Meridian's base proposal for Northstar Appliances." },
  { source: 'vault_street_partners', target: 'northstar', name: 'SUPPORTS_CONDITIONALLY', fact_type: 'covenant_condition', episodes: [LENDER_LETTER],
    fact: 'Vault Street Partners supports the reversible-pilot proposal provided weekly liquidity reports are delivered on schedule.' },
  { source: 'meridian_credit_committee', target: 'northstar', name: 'EVALUATES', fact_type: 'covenant_condition', episodes: [LENDER_LETTER],
    fact: "Meridian Credit Committee is scheduled to evaluate Northstar Appliances' forbearance request within two weeks." },
  { source: 'marcus_lee', target: 'meridian', name: 'NEGOTIATES_WITH', fact_type: 'covenant_condition', episodes: [LENDER_LETTER],
    fact: 'CFO Marcus Lee is the primary liaison negotiating covenant terms with Meridian Lending Group.' },
  { source: 'marcus_lee', target: 'meridian', name: 'REPORTS_LIQUIDITY_TO', fact_type: 'covenant_condition', episodes: [LENDER_LETTER],
    fact: 'Marcus Lee is responsible for submitting the weekly liquidity reports Meridian requires under the proposed covenant terms.' },

  // Leadership / operations cluster
  { source: 'dana_whitfield', target: 'northstar', name: 'LEADS',
    fact: 'Dana Whitfield has served as CEO of Northstar Appliances for six years and is weighing an immediate restructuring against a staged pilot.', fact_type: 'leadership' },
  { source: 'marcus_lee', target: 'northstar', name: 'HOLDS_ROLE_AT',
    fact: 'Marcus Lee serves as Chief Financial Officer of Northstar Appliances and modeled the 11-week liquidity runway.', fact_type: 'employment' },
  { source: 'elena_cho', target: 'northstar', name: 'HOLDS_ROLE_AT',
    fact: 'Elena Cho serves as VP of Supply Chain at Northstar Appliances, coordinating supplier payment protections.', fact_type: 'employment' },
  { source: 'grace_liu', target: 'northstar', name: 'HOLDS_ROLE_AT',
    fact: 'Grace Liu serves as VP of Corporate Communications at Northstar Appliances.', fact_type: 'employment' },
  { source: 'board_of_directors', target: 'northstar', name: 'OVERSEES',
    fact: "Northstar Appliances' seven-member Board of Directors must approve any company-wide restructuring or pilot program.", fact_type: 'governance' },
  { source: 'priya_nandakumar', target: 'toledo_plant', name: 'OPERATES',
    fact: 'Priya Nandakumar manages daily operations at the Toledo Assembly Plant.', fact_type: 'operations' },
  { source: 'robert_hayes', target: 'macon_plant', name: 'OPERATES',
    fact: 'Robert Hayes manages daily operations at the Macon Assembly Plant.', fact_type: 'operations' },
  { source: 'northstar', target: 'toledo_plant', name: 'OPERATES',
    fact: 'Northstar Appliances operates the Toledo Assembly Plant, its primary refrigeration manufacturing site.', fact_type: 'operations' },
  { source: 'northstar', target: 'macon_plant', name: 'OPERATES',
    fact: 'Northstar Appliances operates the Macon Assembly Plant, its laundry appliance manufacturing site.', fact_type: 'operations' },
  { source: 'northstar', target: 'georgia_distribution_center', name: 'OPERATES',
    fact: "Northstar Appliances operates the Georgia Distribution Center supporting the Macon plant's regional shipments.", fact_type: 'operations' },
  { source: 'elena_cho', target: 'karlin_components', name: 'MANAGES_RELATIONSHIP_WITH',
    fact: 'Elena Cho coordinates directly with Karlin Components on payment terms during the proposed pilot.', fact_type: 'supply_agreement' },

  // Supplier cluster
  { source: 'karlin_components', target: 'northstar', name: 'SUPPLIES_TO', fact_type: 'supply_agreement', episodes: [RESTRUCTURING_BENCHMARK],
    fact: "Karlin Components supplies roughly 38% of Northstar Appliances' control-board volume across both plants." },
  { source: 'karlin_components', target: 'toledo_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement', episodes: [RESTRUCTURING_BENCHMARK],
    fact: 'Karlin Components ships control boards directly to the Toledo Assembly Plant.' },
  { source: 'karlin_components', target: 'macon_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement', episodes: [RESTRUCTURING_BENCHMARK],
    fact: 'Karlin Components also ships control boards to the Macon Assembly Plant.' },
  { source: 'ironclad_steel', target: 'toledo_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement',
    fact: 'Ironclad Steel Supply provides raw steel stock to the Toledo Assembly Plant on 30-day payment terms.' },
  { source: 'ironclad_steel', target: 'macon_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement',
    fact: 'Ironclad Steel Supply also ships raw steel stock to the Macon Assembly Plant.' },
  { source: 'bellwood_motors', target: 'macon_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement',
    fact: 'Bellwood Motors Corp supplies compressor motors to the Macon Assembly Plant.' },
  { source: 'vantage_plastics', target: 'toledo_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement',
    fact: 'Vantage Plastics Group supplies molded housings to the Toledo Assembly Plant.' },
  { source: 'precision_fasteners', target: 'toledo_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement',
    fact: 'Precision Fasteners Inc supplies fastening hardware to the Toledo Assembly Plant.' },
  { source: 'summit_electronics', target: 'macon_plant', name: 'SUPPLIES_TO', fact_type: 'supply_agreement',
    fact: 'Summit Electronics Components is being evaluated as a secondary electronics supplier for the Macon Assembly Plant.' },
  { source: 'tom_reyes', target: 'karlin_components', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Tom Reyes serves as Chief Financial Officer of Karlin Components.' },
  { source: 'tom_reyes', target: 'northstar', name: 'WARNS', fact_type: 'supplier_survey', episodes: [RESTRUCTURING_BENCHMARK],
    fact: "Tom Reyes warned that delayed approvals and unclear ownership could cut Northstar's expected cash-burn savings from 18% to as low as 6%." },
  { source: 'precision_fasteners', target: 'northstar', name: 'RAISES_CONCERN_ABOUT', fact_type: 'supplier_survey', episodes: [RESTRUCTURING_BENCHMARK],
    fact: 'Precision Fasteners Inc flagged payment-delay risk to its own operations if the restructuring proceeds without supplier protections.' },
  { source: 'bellwood_motors', target: 'northstar', name: 'RAISES_CONCERN_ABOUT', fact_type: 'supplier_survey', episodes: [RESTRUCTURING_BENCHMARK],
    fact: 'Bellwood Motors Corp cited approval-process delays as a recurring friction point in the supplier survey on restructuring impact.' },
  { source: 'vantage_plastics', target: 'northstar', name: 'RAISES_CONCERN_ABOUT', fact_type: 'supplier_survey', episodes: [RESTRUCTURING_BENCHMARK],
    fact: 'Vantage Plastics Group participated in the supplier survey reporting only a 6% cash-burn reduction due to unclear ownership of approvals.' },
  { source: 'ironclad_steel', target: 'northstar', name: 'REQUESTS_CLARITY_FROM', fact_type: 'supply_agreement',
    fact: 'Ironclad Steel Supply requested clarity on purchase-order continuity during any restructuring pilot.' },
  { source: 'summit_electronics', target: 'karlin_components', name: 'EVALUATED_AS_ALTERNATIVE_TO', fact_type: 'supply_agreement',
    fact: "Summit Electronics Components is being evaluated as a secondary supplier to reduce Northstar's concentration risk with Karlin Components." },

  // Labor cluster
  { source: 'uaw_local_1180', target: 'toledo_plant', name: 'REPRESENTS', fact_type: 'labor_relations',
    fact: 'United Appliance Workers Local 1180 represents assembly-line workers at the Toledo Assembly Plant.' },
  { source: 'uaw_local_2214', target: 'macon_plant', name: 'REPRESENTS', fact_type: 'labor_relations',
    fact: 'United Appliance Workers Local 2214 represents assembly-line workers at the Macon Assembly Plant.' },
  { source: 'denise_ruiz', target: 'toledo_plant', name: 'REPRESENTS', fact_type: 'labor_relations',
    fact: 'Denise Ruiz serves as chief shop steward representing Toledo Assembly Plant workers.' },
  { source: 'uaw_local_1180', target: 'northstar', name: 'NEGOTIATES_WITH', fact_type: 'labor_relations',
    fact: 'United Appliance Workers Local 1180 will accept a time-limited pilot only if it comes with a firm sunset date.' },
  { source: 'uaw_local_2214', target: 'northstar', name: 'NEGOTIATES_WITH', fact_type: 'labor_relations',
    fact: 'United Appliance Workers Local 2214 is pressing for consultation rights before any permanent plant-closure decision.' },
  { source: 'uaw_international', target: 'northstar', name: 'NEGOTIATES_WITH', fact_type: 'labor_relations',
    fact: 'United Appliance Workers International confirmed the labor agreement permits a time-limited pilot but requires consultation before permanent closures.' },
  { source: 'denise_ruiz', target: 'northstar', name: 'NEGOTIATES_WITH', fact_type: 'labor_relations',
    fact: 'Denise Ruiz is the lead negotiator communicating union conditions for accepting a reversible pilot.' },
  { source: 'uaw_local_1180', target: 'uaw_international', name: 'MEMBER_OF', fact_type: 'membership',
    fact: 'United Appliance Workers Local 1180 is a chartered local of the United Appliance Workers International union.' },
  { source: 'uaw_local_2214', target: 'uaw_international', name: 'MEMBER_OF', fact_type: 'membership',
    fact: 'United Appliance Workers Local 2214 is a chartered local of the United Appliance Workers International union.' },
  { source: 'uaw_bargaining_committee', target: 'uaw_international', name: 'MEMBER_OF', fact_type: 'membership',
    fact: 'The Joint Bargaining Committee coordinates Toledo and Macon local positions under the United Appliance Workers International charter.' },
  { source: 'uaw_bargaining_committee', target: 'northstar', name: 'NEGOTIATES_WITH', fact_type: 'labor_relations',
    fact: "The Joint Bargaining Committee is coordinating a unified union position ahead of Northstar's restructuring decision." },
  { source: 'jordan_ellis', target: 'uaw_local_1180', name: 'MEMBER_OF', fact_type: 'membership',
    fact: 'Jordan Ellis was a member of United Appliance Workers Local 1180 before being laid off in a prior cost round.' },
  { source: 'jordan_ellis', target: 'northstar', name: 'COMMENTS_ON', fact_type: 'public_sentiment',
    fact: 'Jordan Ellis, a laid-off Toledo engineer, publicly criticized unclear communication around the prior round of workforce cuts.' },

  // Retail cluster
  { source: 'homeplex', target: 'northstar', name: 'PARTNERS_WITH', fact_type: 'retail_partnership',
    fact: "HomePlex Retail Corp accounts for 27% of Northstar Appliances' unit sales and is monitoring supply-continuity risk." },
  { source: 'alicia_brooks', target: 'homeplex', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Alicia Brooks serves as VP of Merchandising at HomePlex Retail Corp.' },
  { source: 'alicia_brooks', target: 'northstar', name: 'REQUESTS_CLARITY_FROM', fact_type: 'retail_partnership',
    fact: "Alicia Brooks requested a written continuity plan from Northstar before committing to next season's purchase orders." },
  { source: 'bigbox_home', target: 'northstar', name: 'PARTNERS_WITH', fact_type: 'retail_partnership',
    fact: "BigBox Home Retail is a secondary retail channel watching Northstar's restructuring decision as a signal for shifting orders to competitors." },
  { source: 'regional_hardware_coop', target: 'northstar', name: 'PARTNERS_WITH', fact_type: 'retail_partnership',
    fact: 'Regional Hardware Co-op represents independent dealers concerned about parts availability during any restructuring pilot.' },

  // Customer cluster
  { source: 'northstar_loyalists', target: 'northstar', name: 'RAISES_CONCERN_ABOUT', fact_type: 'customer_sentiment',
    fact: 'The Northstar Loyalists community, roughly 40,000 members, voiced concern over warranty and service continuity amid restructuring speculation.' },
  { source: 'price_sensitive_households', target: 'northstar', name: 'RAISES_CONCERN_ABOUT', fact_type: 'customer_sentiment',
    fact: 'The price-sensitive household segment expressed concern that restructuring costs could be passed on through price increases.' },
  { source: 'appliance_repair_community', target: 'northstar', name: 'RAISES_CONCERN_ABOUT', fact_type: 'customer_sentiment',
    fact: 'Independent repair technicians in the Appliance Repair Community Forum discussed parts-supply risk tied to the restructuring decision.' },
  { source: 'toledo_community_advocates', target: 'uaw_local_1180', name: 'ADVOCATES_FOR', fact_type: 'community_advocacy',
    fact: 'Toledo Community Advocates organized public comment sessions in support of Toledo Assembly Plant workers ahead of any closure announcement.' },

  // Media cluster
  { source: 'midwest_business_journal', target: 'northstar', name: 'REPORTS_ON', fact_type: 'media_coverage',
    fact: "Midwest Business Journal first reported Northstar Appliances' roughly 11-week liquidity runway estimate." },
  { source: 'sam_okafor', target: 'midwest_business_journal', name: 'HOLDS_ROLE_AT', fact_type: 'employment',
    fact: 'Sam Okafor is an industry journalist on staff at Midwest Business Journal.' },
  { source: 'sam_okafor', target: 'northstar', name: 'REPORTS_ON', fact_type: 'media_coverage',
    fact: 'Sam Okafor covered both the restructuring decision and the supplier survey findings on cash-burn impact.' },
  { source: 'appliance_trade_press', target: 'northstar', name: 'CITES', fact_type: 'media_coverage', episodes: [RESTRUCTURING_BENCHMARK],
    fact: "Appliance Trade Press published the industry benchmark finding that staged restructuring programs cut cash burn by 18% within 90 days, a figure central to Northstar's pilot proposal." },
  { source: 'trade_wire_newsletter', target: 'meridian', name: 'REPORTS_ON', fact_type: 'media_coverage',
    fact: "Trade Wire Newsletter tracks lender and union reactions across the appliance manufacturing sector, including Meridian Lending Group's covenant position." },
  { source: 'local_toledo_news12', target: 'toledo_plant', name: 'REPORTS_ON', fact_type: 'media_coverage',
    fact: 'Local Toledo News 12 covered community reaction in Toledo to the potential restructuring of the Toledo Assembly Plant.' },

  // Self loops (internal processes) - exercise self-loop rendering/grouping
  { source: 'northstar', target: 'northstar', name: 'UNDERGOES_STRATEGY_REVIEW', fact_type: 'internal_process',
    fact: "Northstar Appliances' leadership team conducts an internal quarterly strategy review to weigh restructuring options against the reversible pilot proposal." },
  { source: 'meridian', target: 'meridian', name: 'CONDUCTS_INTERNAL_COMPLIANCE_REVIEW', fact_type: 'internal_process', episodes: [LENDER_LETTER],
    fact: "Meridian Lending Group's credit committee periodically reviews its own covenant compliance monitoring process for large syndicated loans." },
  { source: 'uaw_international', target: 'uaw_international', name: 'HOLDS_INTERNAL_RATIFICATION_VOTE', fact_type: 'internal_process',
    fact: 'United Appliance Workers International periodically holds an internal ratification vote among its locals before approving strategic labor agreements.' }
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
    episodes: def.episodes || [LIQUIDITY_FILING],
    created_at: ts(createdOffset),
    valid_at: ts(createdOffset - VALID_AT_LEAD_SECONDS)
  }
})

export default { nodes, edges }
