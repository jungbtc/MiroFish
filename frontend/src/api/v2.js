import service from './index'

/** Load the complete, durable decision state for a run. */
export const getDecisionRun = (runId) => {
  return service.get(`/api/v2/runs/${encodeURIComponent(runId)}`)
}

/** Continue a completed core report into its durable research/refinement state. */
export const getCoreRefinement = (reportId) => {
  return service.get(`/api/v2/core/reports/${encodeURIComponent(reportId)}/refinement`)
}

export const startCoreResearch = (reportId, retry = false) => {
  return service.post(`/api/v2/core/reports/${encodeURIComponent(reportId)}/research/start`, { retry })
}

export const syncCoreResearch = (reportId) => {
  return service.post(`/api/v2/core/reports/${encodeURIComponent(reportId)}/research/sync`)
}

export const cancelCoreResearch = (reportId) => {
  return service.post(`/api/v2/core/reports/${encodeURIComponent(reportId)}/research/cancel`)
}

/**
 * Record a private/internal answer. The response contains the recomputed run
 * state, including branch deltas, stop evaluation, memo, and audit events.
 */
export const submitInternalAnswer = (runId, data) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/answers`, data)
}

/** Re-run the explainable continue-or-stop evaluation. */
export const evaluateDecisionStop = (runId) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/stop/evaluate`)
}

/** Download the current executive memo as Markdown. */
export const getDecisionMemo = (runId) => {
  return service.get(`/api/v2/runs/${encodeURIComponent(runId)}/report.md`, {
    responseType: 'text'
  })
}
