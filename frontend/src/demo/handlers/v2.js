// Demo fixture handlers for the v2 decision-refinement API.
//
// The six states in fixtures/v2 were captured from the real deterministic
// backend pipeline (POST /api/v2/demo plus the scripted mutations) and play
// back as a fixed sequence: a persisted pointer advances one step per
// workflow mutation, so the DecisionWorkspace walks the same journey the
// live backend produces — internal answer → action confirmation → model
// confirmation (Monte Carlo) → owner assignment → stop evaluation.
import { getV2Index, advanceV2Index } from '../clock.js'
import { v2States } from '../fixtures/v2/index.js'

const current = () => v2States[Math.min(getV2Index(), v2States.length - 1)]
const advance = () => v2States[advanceV2Index(v2States.length)]

// Real backend wraps some mutation payloads as {run: state}; GETs and
// answers return the state directly. normalizeRunResponse accepts both,
// but we mirror the live shapes anyway.
export const routes = [
  {
    method: 'get',
    pattern: /^\/api\/v2\/core\/reports\/(?<reportId>[^/?]+)\/refinement$/,
    latency: 'read',
    handler: () => current()
  },
  {
    method: 'get',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)$/,
    latency: 'read',
    handler: () => current()
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/fork$/,
    latency: 'read',
    // The captured run is already internal, so the UI never forks; if it
    // ever does, hand back the current state unchanged.
    handler: () => ({ __status: 201, data: current() })
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/answers$/,
    latency: 'ai',
    handler: () => advance()
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/actions\/confirm$/,
    latency: 'ai',
    handler: () => ({ run: advance() })
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/decision-model\/confirm$/,
    latency: 'ai',
    handler: () => {
      const state = advance()
      return { analysis: state.decision_analysis_result, run: state }
    }
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/decision-analysis\/waive$/,
    latency: 'ai',
    handler: () => ({ run: advance() })
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/execution-owners$/,
    latency: 'ai',
    handler: () => ({ run: advance() })
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/decision-analysis\/evaluate$/,
    latency: 'ai',
    handler: () => {
      const state = current()
      return { analysis: state.decision_analysis_result, run: state }
    }
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/stop\/evaluate$/,
    latency: 'ai',
    handler: () => current()
  },
  {
    method: 'post',
    pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/internal-questions$/,
    latency: 'ai',
    // The captured question budget is closed; proposals just echo the
    // current state so the UI reports the queue as already satisfied.
    handler: () => current()
  }
]
