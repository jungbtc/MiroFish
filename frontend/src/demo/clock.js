// Scripted-job state machine for demo mode.
//
// Job progress is derived from wall-clock elapsed time (not poll count), so
// it doesn't matter how often a component polls or whether the tab was
// backgrounded. State is persisted to sessionStorage so a mid-job refresh
// resumes instead of restarting. When sessionStorage isn't available (e.g.
// this module imported from a plain Node test) state falls back to an
// in-memory object for the lifetime of the process.

const STORAGE_KEY = 'forefold.demo.jobs.v1'

let nowFn = () => Date.now()
let memoryState = null

const resolveStorage = () => {
  if (typeof sessionStorage === 'undefined') return null
  try {
    return sessionStorage
  } catch {
    return null
  }
}

const emptyState = () => ({ jobs: {}, v2Index: 0 })

const readState = () => {
  const storage = resolveStorage()
  if (!storage) return memoryState || (memoryState = emptyState())

  try {
    const raw = storage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : emptyState()
  } catch {
    return emptyState()
  }
}

const writeState = state => {
  const storage = resolveStorage()
  if (!storage) {
    memoryState = state
    return
  }

  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Storage can be full/unavailable (private browsing, quota); keep going
    // with an in-memory copy rather than throwing out of a demo handler.
    memoryState = state
  }
}

// Records Date.now() for `name` unless it's already started.
export const startJob = name => {
  const state = readState()
  if (!state.jobs[name]) {
    state.jobs[name] = { startedAt: nowFn() }
    writeState(state)
  }
  return state.jobs[name].startedAt
}

// startJob + return name; lets a poll handler auto-start a job on first call
// (e.g. after a refresh or a deep link straight into a running step).
export const ensureJob = name => {
  startJob(name)
  return name
}

// For read/poll handlers reached WITHOUT the mutation that normally starts
// the job (a deep link or a fresh session): backdate the job past its full
// duration so the page shows the completed state instead of replaying the
// progression from zero. A no-op when the job already started via the
// normal flow, so live scripted progressions are unaffected.
export const ensureCompletedJob = (name, durationSec) => {
  const state = readState()
  if (!state.jobs[name]) {
    state.jobs[name] = { startedAt: nowFn() - ((durationSec || 0) + 5) * 1000 }
    writeState(state)
  }
  return name
}

export const jobStarted = name => Boolean(readState().jobs[name])

// Seconds since `name` started, or null if it hasn't started.
export const jobElapsed = name => {
  const job = readState().jobs[name]
  if (!job) return null
  return (nowFn() - job.startedAt) / 1000
}

// 0..1 clamped; 0 if the job hasn't started yet.
export const jobFraction = (name, durationSec) => {
  const elapsed = jobElapsed(name)
  if (elapsed === null) return 0
  if (!durationSec || durationSec <= 0) return 1
  return Math.min(1, Math.max(0, elapsed / durationSec))
}

export const resetJob = name => {
  const state = readState()
  if (state.jobs[name]) {
    delete state.jobs[name]
    writeState(state)
  }
}

export const resetAll = () => {
  writeState(emptyState())
}

// Pointer into a scripted sequence of v2 decision-run states, also
// persisted so it survives a refresh mid-sequence.
export const getV2Index = () => readState().v2Index || 0

export const advanceV2Index = max => {
  const state = readState()
  const current = state.v2Index || 0
  const bounded = typeof max === 'number' && max > 0
  const next = bounded ? Math.min(current + 1, max - 1) : current + 1
  state.v2Index = next
  writeState(state)
  return next
}

// Test-only escape hatches: inject a fake clock and clear all state
// (sessionStorage-backed or in-memory) between test cases.
export const __testHooks = {
  setNow: fn => {
    nowFn = typeof fn === 'function' ? fn : () => Date.now()
  },
  reset: () => {
    memoryState = null
    nowFn = () => Date.now()
    const storage = resolveStorage()
    if (storage) {
      try {
        storage.removeItem(STORAGE_KEY)
      } catch {
        // Session storage can be unavailable in hardened browser contexts.
      }
    }
  }
}
