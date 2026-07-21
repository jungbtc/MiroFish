// Phase 4 (report generation) fixture: the scripted console-output timeline
// for the Northstar Appliances report run. Consumed by
// src/demo/handlers/phase345.js for GET /api/report/:id/console-log.
//
// Unlike agentLog.js, these are PLAIN STRINGS (not objects) once revealed —
// `at` here is just this module's own bookkeeping so the handler can decide
// which lines are visible yet, as a fraction (0..1) of REPORT_SECONDS.

const LINES = [
  'Report agent started for simulation sim_demo_northstar',
  'Loading simulation context and graph snapshot...',
  'Graph snapshot loaded: 42 nodes, 68 edges',
  'Resolved report id: report_demo_northstar',
  'Planning report outline...',
  'Outline finalized: 6 sections',

  'Section 1/6: Executive Summary - starting',
  'Invoking tool: insight_forge',
  'insight_forge query dispatched',
  'insight_forge completed in 1.6s',
  'Parsing tool result (1842 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 1/6 complete: Executive Summary',

  'Section 2/6: Public Sentiment Timeline - starting',
  'Invoking tool: panorama_search',
  'panorama_search query dispatched',
  '__WARNING__panorama_search response delayed, retrying once',
  'panorama_search completed in 2.4s',
  'Parsing tool result (1523 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 2/6 complete: Public Sentiment Timeline',

  'Section 3/6: Stakeholder Positions - starting',
  'Invoking tool: interview_agents',
  'Dispatching 3 interview prompts (agents 0, 6, 7)',
  'interview_agents completed in 4.1s',
  'Parsing tool result (3210 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 3/6 complete: Stakeholder Positions',

  'Section 4/6: Risk Scenarios - starting',
  'Invoking tool: quick_search',
  'quick_search query dispatched',
  'quick_search completed in 1.1s',
  'Parsing tool result (980 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 4/6 complete: Risk Scenarios',

  'Section 5/6: Pilot vs Full Restructuring Comparison - starting',
  'Invoking tool: get_graph_statistics',
  'get_graph_statistics query dispatched',
  'get_graph_statistics completed in 0.7s',
  'Parsing tool result (312 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 5/6 complete: Pilot vs Full Restructuring Comparison',

  'Section 6/6: Recommendation - starting',
  'Invoking tool: get_entities_by_type',
  'get_entities_by_type query dispatched',
  'get_entities_by_type completed in 0.5s',
  'Parsing tool result (188 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 6/6 complete: Recommendation',

  'All sections complete, assembling final report...',
  'Validating markdown output...',
  'Persisting report report_demo_northstar',
  'Report generation complete for report_demo_northstar',
  'Report agent shutting down'
]

const consoleLog = LINES.map((raw, index) => {
  const isWarning = raw.startsWith('__WARNING__')
  const text = isWarning ? raw.slice('__WARNING__'.length) : raw
  const level = isWarning ? 'WARNING' : 'INFO'

  return {
    at: Math.min(0.99, (index / (LINES.length - 1)) * 0.99),
    line: `[${level}] ${text}`
  }
})

export default consoleLog
