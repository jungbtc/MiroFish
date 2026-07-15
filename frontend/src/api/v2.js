import service from './index'

/**
 * Import a completed Deep Research report and create a decision-intelligence run.
 * The backend accepts PDF/Markdown uploads as multipart data and structured
 * research documents as JSON files.
 */
export const importDeepResearch = (formData) => {
  return service.post('/api/v2/research-pack', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600000
  })
}

/** Load the complete, durable decision state for a run. */
export const getDecisionRun = (runId) => {
  return service.get(`/api/v2/runs/${encodeURIComponent(runId)}`)
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
