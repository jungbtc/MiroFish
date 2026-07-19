import service from './index'

/** Load the complete, durable decision state for a run. */
export const getDecisionRun = (runId) => {
  return service.get(`/api/v2/runs/${encodeURIComponent(runId)}`)
}

/** Load the readable parent/child lineage for an existing decision run. */
export const getDecisionRunLineage = (runId) => {
  return service.get(`/api/v2/runs/${encodeURIComponent(runId)}/lineage`)
}

/** Continue a completed core report into its bounded decision-refinement state. */
export const getCoreRefinement = (reportId) => {
  return service.get(`/api/v2/core/reports/${encodeURIComponent(reportId)}/refinement`)
}

/** Fork a sealed public baseline into the private, mutable refinement lineage. */
export const forkDecisionRun = (runId) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/fork`, {})
}

/**
 * Record a private/internal answer. The response contains the recomputed run
 * state, including branch deltas, stop evaluation, memo, and audit events.
 */
export const submitInternalAnswer = (runId, data) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/answers`, data)
}

/** Propose a missing private question for priority review within the fixed question budget. */
export const proposeInternalQuestion = (runId, data) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/internal-questions`, data)
}

/** Confirm that every reconstructed path is a real action considered by management. */
export const confirmDecisionActions = (runId, data) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/actions/confirm`, data)
}

/** Assign named owners to the remaining validation and expansion-gate stages. */
export const assignExecutionOwners = (runId, data) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/execution-owners`, data)
}

/** Apply explicit human confirmations to the current decision-model proposal. */
export const confirmDecisionModel = (runId, data) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/decision-model/confirm`, data)
}

/** Recalculate the already confirmed model with bounded deterministic settings. */
export const evaluateDecisionAnalysis = (runId, data = {}) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/decision-analysis/evaluate`, data)
}

/** Explicitly finalize the evidence-backed qualitative path without numeric utility claims. */
export const waiveQuantitativeDecisionAnalysis = (runId, data) => {
  return service.post(`/api/v2/runs/${encodeURIComponent(runId)}/decision-analysis/waive`, data)
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
