// Shared scenario constants for demo fixture handlers. Import these instead
// of inventing new IDs/timestamps so every handler module tells one
// consistent story.

export const IDS = {
  projectId: 'proj_demo_northstar',
  graphId: 'graph_demo_northstar',
  simulationId: 'sim_demo_northstar',
  reportId: 'report_demo_northstar'
}

export const REQUIREMENT = 'Assess public and stakeholder reaction if Northstar Appliances announces an immediate company-wide restructuring versus a staged reversible pilot, and recommend how to proceed.'

export const BASE_TIME = '2026-07-01T09:00:00.000Z'

export const ts = offsetSec => new Date(Date.parse(BASE_TIME) + offsetSec * 1000).toISOString()
