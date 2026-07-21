// Demo fixture: GET /api/simulation/history rows, consumed by
// src/components/HistoryDatabase.vue. Each entry needs project_id (enables
// the Step1 button), report_id (enables the Step4 button), and
// current_round/total_rounds (drives the "completed" vs "in-progress"
// styling and the rounds-progress label).
//
// Entry 1 is the fully completed Y Combinator / AGI-era run that the rest of
// the demo fixtures (project.js/graph.js/profiles.js/simConfig.js) describe
// in depth. Entry 2 is an unrelated, still-in-progress decoy so the history
// list doesn't look like a single hard-coded row.

import { IDS, REQUIREMENT, ts } from './scenario.js'

export default [
  {
    simulation_id: IDS.simulationId,
    project_id: IDS.projectId,
    report_id: IDS.reportId,
    simulation_requirement: REQUIREMENT,
    created_at: ts(-86400),
    current_round: 10,
    total_rounds: 10,
    files: [
      { filename: 'yc_batch_composition_2023_2026.pdf' },
      { filename: 'agent_leverage_telemetry_study.pdf' },
      { filename: 'post_batch_quality_audit.md' }
    ]
  },
  {
    simulation_id: 'sim_demo_ycrobotics',
    project_id: 'proj_demo_ycrobotics',
    report_id: null,
    simulation_requirement: "Should YC run a dedicated robotics batch? Simulate founder and partner reaction to carving out a hardware-and-robotics-focused track alongside the AGI-Native Track.",
    created_at: ts(-3600),
    current_round: 4,
    total_rounds: 40,
    files: [
      { filename: 'robotics_track_proposal_notes.pdf' }
    ]
  }
]
