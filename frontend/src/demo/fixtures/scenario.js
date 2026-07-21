// Shared scenario constants for demo fixture handlers. Import these instead
// of inventing new IDs/timestamps so every handler module tells one
// consistent story.

export const IDS = {
  projectId: 'proj_demo_ycagi',
  graphId: 'graph_demo_ycagi',
  simulationId: 'sim_demo_ycagi',
  reportId: 'report_demo_ycagi'
}

export const REQUIREMENT = 'Y Combinator is deciding how to prepare for the AGI era: simulate how founders, partners, LPs, and frontier-lab researchers react if YC commits to an AGI-native selection and batch model — weighting agent leverage over headcount, admitting far more agent-augmented tiny teams, and adding an AGI-native curriculum — versus keeping the classic batch playbook, and recommend what YC should do for the Winter 2027 batch and which applicant profile it should prioritize.'

export const BASE_TIME = '2026-07-01T09:00:00.000Z'

export const ts = offsetSec => new Date(Date.parse(BASE_TIME) + offsetSec * 1000).toISOString()
