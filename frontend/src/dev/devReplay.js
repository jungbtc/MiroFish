const REPLAY_QUERY_VALUE = '1'
const REPLAY_SESSION_KEY = 'forefold.devReplay.manifest.v1'

export const DEV_REPLAY_MUTATION_BLOCKED = 'DEV_REPLAY_MUTATION_BLOCKED'

const COMPLETE_RUN_STATUSES = new Set(['completed', 'degraded', 'stopped'])

const runtimeEnv = () => import.meta.env ?? {}

const cleanId = value => String(value ?? '').trim()

const replayQueryValue = location => {
  const routeValue = location?.query?.replay
  if (Array.isArray(routeValue)) return routeValue[0]
  if (routeValue !== undefined) return routeValue

  const search = typeof location === 'string'
    ? location
    : location?.search ?? (typeof window !== 'undefined' ? window.location.search : '')

  try {
    return new URLSearchParams(search).get('replay')
  } catch {
    return null
  }
}

const resolveSessionStorage = storage => {
  if (storage) return storage
  if (typeof window === 'undefined') return null
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

export const normalizeReplayManifest = manifest => {
  if (!manifest || typeof manifest !== 'object') return null

  const normalized = {
    projectId: cleanId(manifest.projectId ?? manifest.project_id),
    simulationId: cleanId(manifest.simulationId ?? manifest.simulation_id),
    reportId: cleanId(manifest.reportId ?? manifest.report_id),
    refinementRunId: cleanId(manifest.refinementRunId ?? manifest.refinement_run_id),
    title: cleanId(manifest.title ?? manifest.project_name ?? manifest.simulation_requirement),
    createdAt: cleanId(manifest.createdAt ?? manifest.created_at)
  }

  if (!normalized.projectId && !normalized.simulationId && !normalized.reportId && !normalized.refinementRunId) {
    return null
  }
  return normalized
}

export const isDevReplayEnabled = (env = runtimeEnv()) => {
  const explicit = String(env?.VITE_ENABLE_DEV_REPLAY ?? '').toLowerCase()
  return Boolean(env?.DEV) || explicit === 'true' || explicit === '1'
}

export const isDevReplayActive = (location, env = runtimeEnv()) => {
  return isDevReplayEnabled(env) && String(replayQueryValue(location)) === REPLAY_QUERY_VALUE
}

export const isReplayMutationBlocked = (requestOrMethod, activeOrLocation, env = runtimeEnv()) => {
  const active = typeof activeOrLocation === 'boolean'
    ? activeOrLocation
    : isDevReplayActive(activeOrLocation, env)
  if (!active) return false
  const method = typeof requestOrMethod === 'string'
    ? requestOrMethod
    : requestOrMethod?.method
  return String(method || '').toLowerCase() !== 'get'
}

export const getReplayManifest = storage => {
  const target = resolveSessionStorage(storage)
  if (!target) return null

  try {
    const raw = target.getItem(REPLAY_SESSION_KEY)
    return raw ? normalizeReplayManifest(JSON.parse(raw)) : null
  } catch {
    return null
  }
}

export const setReplayManifest = (manifest, storage) => {
  const normalized = normalizeReplayManifest(manifest)
  if (!normalized) throw new TypeError('Replay manifest requires at least one saved workflow ID.')

  const target = resolveSessionStorage(storage)
  if (!target) return normalized
  target.setItem(REPLAY_SESSION_KEY, JSON.stringify(normalized))
  return normalized
}

export const clearReplayManifest = storage => {
  const target = resolveSessionStorage(storage)
  if (!target) return
  try {
    target.removeItem(REPLAY_SESSION_KEY)
  } catch {
    // Session storage can be unavailable in hardened browser contexts.
  }
}

export const buildReplayTarget = (phase, manifest) => {
  const replay = normalizeReplayManifest(manifest)
  const query = {
    replay: REPLAY_QUERY_VALUE,
    ...(replay?.projectId ? { project: replay.projectId } : {}),
    ...(replay?.simulationId ? { simulation: replay.simulationId } : {}),
    ...(replay?.reportId ? { report: replay.reportId } : {}),
    ...(replay?.refinementRunId ? { run: replay.refinementRunId } : {})
  }

  if (phase === 'intake') return { name: 'Home', query }
  if (!replay) return null

  const targets = {
    knowledge: replay.projectId
      ? { name: 'Process', params: { projectId: replay.projectId }, query }
      : null,
    setup: replay.simulationId
      ? { name: 'Simulation', params: { simulationId: replay.simulationId }, query }
      : null,
    simulation: replay.simulationId
      ? {
          name: 'SimulationRun',
          params: { simulationId: replay.simulationId },
          query
        }
      : null,
    report: replay.reportId
      ? { name: 'Report', params: { reportId: replay.reportId }, query }
      : null,
    decision: replay.refinementRunId
      ? { name: 'DecisionWorkspace', params: { runId: replay.refinementRunId }, query }
      : null
  }

  return targets[phase] ?? null
}

export const getReplayPhases = manifest => {
  const definitions = [
    ['intake', 'Intake'],
    ['knowledge', 'Knowledge'],
    ['setup', 'Setup'],
    ['simulation', 'Simulation'],
    ['report', 'Report'],
    ['decision', 'Decision']
  ]

  return definitions.map(([id, label], index) => {
    const target = buildReplayTarget(id, manifest)
    return {
      id,
      label,
      step: index + 1,
      target,
      available: Boolean(target)
    }
  })
}

export const selectReplayCandidates = history => {
  const entries = Array.isArray(history) ? history : []

  return entries
    .filter(entry => {
      if (!entry || !entry.project_id || !entry.simulation_id || !entry.report_id) return false

      const runnerStatus = cleanId(entry.runner_status).toLowerCase()
      const currentRound = Number(entry.current_round || 0)
      const totalRounds = Number(entry.total_rounds || 0)
      const roundsComplete = totalRounds > 0 && currentRound >= totalRounds

      // Older imported bundles may not contain runner_status; a completed
      // round count plus an attached report remains a valid replay artifact.
      return COMPLETE_RUN_STATUSES.has(runnerStatus) || roundsComplete || !runnerStatus
    })
    .map(entry => ({
      ...entry,
      projectId: cleanId(entry.project_id),
      simulationId: cleanId(entry.simulation_id),
      reportId: cleanId(entry.report_id),
      title: cleanId(entry.project_name || entry.simulation_requirement) || 'Untitled completed run',
      createdAt: cleanId(entry.created_at)
    }))
    .sort((left, right) => {
      const rightTime = Date.parse(right.createdAt) || 0
      const leftTime = Date.parse(left.createdAt) || 0
      return rightTime - leftTime
    })
}

export const selectLatestReplayRunId = (lineage, fallbackRunId = '') => {
  const children = Array.isArray(lineage?.children) ? lineage.children : []
  const rankedChildren = children
    .map((child, index) => ({
      child,
      index,
      timestamp: Date.parse(child?.updated_at || child?.created_at || '') || 0,
      revision: Number(child?.state_revision || 0)
    }))
    .filter(entry => cleanId(entry.child?.run_id))
    .sort((left, right) => {
      if (right.timestamp !== left.timestamp) return right.timestamp - left.timestamp
      if (right.revision !== left.revision) return right.revision - left.revision
      return right.index - left.index
    })

  return cleanId(rankedChildren[0]?.child?.run_id) || cleanId(fallbackRunId)
}

export const DEV_REPLAY_SESSION_KEY = REPLAY_SESSION_KEY
