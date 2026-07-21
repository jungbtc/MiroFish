// Phase 4 (report generation) fixture: the scripted console-output timeline
// for the "Y Combinator in the AGI era" report run. Consumed by
// src/demo/handlers/phase345.js for GET /api/report/:id/console-log.
//
// Unlike agentLog.js, these are PLAIN STRINGS (not objects) once revealed —
// `at` here is just this module's own bookkeeping so the handler can decide
// which lines are visible yet, as a fraction (0..1) of REPORT_SECONDS.

const LINES = [
  'Report agent started for simulation sim_demo_ycagi',
  'Loading simulation context and graph snapshot...',
  'Graph snapshot loaded: 42 nodes, 71 edges',
  'Resolved report id: report_demo_ycagi',
  'Planning report outline...',
  'Outline finalized: 6 sections',

  'Section 1/6: Coverage View: Y Combinator in the AGI Transition - starting',
  'Invoking tool: insight_forge',
  'insight_forge query dispatched',
  'insight_forge completed in 1.7s',
  'Parsing tool result (2015 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 1/6 complete: Coverage View: Y Combinator in the AGI Transition',

  'Section 2/6: What the Simulation Surfaced: Discourse & Sentiment Arc - starting',
  'Invoking tool: panorama_search',
  'panorama_search query dispatched',
  '__WARNING__panorama_search response delayed, retrying once',
  'panorama_search completed in 2.6s',
  'Parsing tool result (1780 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 2/6 complete: What the Simulation Surfaced: Discourse & Sentiment Arc',

  'Section 3/6: Stakeholder Book - starting',
  'Invoking tool: interview_agents',
  'Dispatching 3 interview prompts (agents 0, 7, 3)',
  'interview_agents completed in 4.3s',
  'Parsing tool result (3450 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 3/6 complete: Stakeholder Book',

  'Section 4/6: Scenario Analysis - starting',
  'Invoking tool: quick_search',
  'quick_search query dispatched',
  'quick_search completed in 1.2s',
  'Parsing tool result (1120 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 4/6 complete: Scenario Analysis',

  'Section 5/6: The AGI-Era Applicant Profile - starting',
  'Invoking tool: get_graph_statistics',
  'get_graph_statistics query dispatched',
  'get_graph_statistics completed in 0.8s',
  'Parsing tool result (340 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 5/6 complete: The AGI-Era Applicant Profile',

  'Section 6/6: Recommendation & 12-Month Roadmap - starting',
  'Invoking tool: get_entities_by_type',
  'get_entities_by_type query dispatched',
  'get_entities_by_type completed in 0.6s',
  'Parsing tool result (210 chars)',
  'Drafting section content with LLM...',
  'LLM response received (iteration 1)',
  'Section 6/6 complete: Recommendation & 12-Month Roadmap',

  'All sections complete, assembling final report...',
  'Validating markdown output...',
  'Persisting report report_demo_ycagi',
  'Report generation complete for report_demo_ycagi',
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
