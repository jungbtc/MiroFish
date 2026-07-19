export function numericValue(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function scorePercent(value) {
  const score = numericValue(value)
  const percent = Math.abs(score) <= 1 ? score * 100 : score
  return Math.max(0, Math.min(100, percent))
}

export function formatScore(value) {
  return `${Math.round(scorePercent(value))}%`
}

export function hypothesisDelta(hypothesis = {}) {
  const explicit = Number(hypothesis.last_change)
  if (Number.isFinite(explicit)) return explicit

  const current = numericValue(hypothesis.support_score)
  const previous = Number(hypothesis.previous_score)
  return Number.isFinite(previous) ? Number((current - previous).toFixed(8)) : 0
}

export function branchTone(hypothesis = {}) {
  if (String(hypothesis.status).toLowerCase() === 'pruned') return 'pruned'
  const delta = hypothesisDelta(hypothesis)
  if (delta > 0.0001) return 'strengthened'
  if (delta < -0.0001) return 'weakened'
  return 'unchanged'
}

export function formatDelta(value) {
  const delta = numericValue(value)
  const points = Math.abs(delta) <= 1 ? delta * 100 : delta
  if (Math.abs(points) < 0.05) return 'No change'
  return `${points > 0 ? '+' : ''}${points.toFixed(1)} pts`
}

const ACTION_VERB = /^(approve|proceed|expand|accelerate|pause|defer|postpone|cancel|invest|launch|pilot|run|stage|redesign|revise|modify|adopt|prioritize|enter|maintain|stop|build|reduce|increase|acquire|divest|partner|fund|commit|implement|execute|scale|consolidate|exit|wait|hold|reject|choose|select|retain|restructure)\b/i
const ACTION_NOUN = /\b(expansion|investment|launch|rollout|pilot|trial|redesign|revision|cancellation|postponement|pause|deferral|acquisition|divestiture|partnership|commitment|buildout|restructuring|exit|consolidation|deployment|program|initiative)\b/i
const OBSERVATION_PREFIX = /^(the\s+)?(market|demand|revenue|sales|customers?|competitors?|cycle|peak|outlook|results?)\b|^(have|has|had|driven|reported|remains?|shows?|indicates?|suggests?)\b/i
const STAKEHOLDER_ONLY = /^(?:(?:approve|choose|select|retain|recommend)\s+)?(?:(?:the|a|an|store|frontline|current|prospective|non)[ -]+)*(?:customers?|members?|non[ -]?members?|employees?|baristas?|managers?|investors?|unions?|regulators?|competitors?|suppliers?|consumers?|stakeholders?)$/i

/**
 * A final recommendation must be something management can select, fund, pause,
 * or execute. This deliberately rejects common market-observation fragments so
 * the executive page fails closed instead of presenting prose as a decision.
 */
export function looksLikeExecutableAction(value) {
  const label = String(value || '').replace(/[*_`#>]/g, '').trim()
  if (label.length < 4 || label.length > 160 || label.endsWith('?')) return false
  if (OBSERVATION_PREFIX.test(label)) return false
  if (STAKEHOLDER_ONLY.test(label)) return false
  return ACTION_VERB.test(label) || ACTION_NOUN.test(label)
}

export function evidencePosture({
  sourcedClaims = 0,
  openContradictions = 0,
  internalEvidenceComplete = false,
  isFinal = false,
  actionIsExecutable = false
} = {}) {
  if (internalEvidenceComplete) return 'Internal evidence complete'
  if (!actionIsExecutable) return 'Incomplete'
  if (!isFinal || openContradictions > 0 || sourcedClaims < 2) return 'Conditional'
  return 'Decision-ready'
}

export function buildExecutiveActionPlan({
  recommendedAction = '',
  actionIsExecutable = false,
  actionsConfirmed = false,
  isReady = false,
  openQuestions = [],
  watchpoint = ''
} = {}) {
  const steps = []

  if (actionIsExecutable && actionsConfirmed) {
    steps.push({
      phase: 'Now',
      title: `${isReady ? 'Approve' : 'Prepare'}: ${recommendedAction}`,
      detail: isReady
        ? 'Record the scope, capital boundary, accountable executive, and first release of resources.'
        : 'Keep the direction provisional until the open approval gates below are resolved.',
      owner: 'Executive sponsor',
      state: isReady ? 'Approve' : 'Provisional'
    })
  } else if (actionIsExecutable) {
    steps.push({
      phase: 'Action gate',
      title: 'Confirm the management action set',
      detail: 'Verify that every reconstructed path is a real option management can approve, fund, pause, or reject.',
      owner: 'Decision owner',
      state: 'Required'
    })
  } else {
    steps.push({
      phase: 'Before approval',
      title: 'Confirm executable decision paths',
      detail: 'Rewrite the choices as mutually exclusive management actions that can be approved, paused, or rejected.',
      owner: 'Decision owner',
      state: 'Required'
    })
  }

  for (const question of openQuestions.slice(0, 2)) {
    steps.push({
      phase: `Gate ${String(steps.length).padStart(2, '0')}`,
      title: String(question.question || 'Resolve the remaining approval condition').replace(/\?+$/, ''),
      detail: question.expected_change || question.rationale || 'Resolve this condition before the decision is released.',
      owner: question.owner_hint || 'Decision owner',
      state: 'Open'
    })
  }

  if (steps.length < 3) {
    steps.push({
      phase: 'Mobilize',
      title: 'Assign an accountable operator and first checkpoint',
      detail: 'Translate the decision into a dated first tranche with one owner, a budget boundary, and a measurable milestone.',
      owner: 'Operating lead',
      state: isReady ? 'Next' : 'Draft'
    })
  }

  if (steps.length < 3) {
    steps.push({
      phase: 'Monitor',
      title: 'Set the pause and reversal trigger',
      detail: watchpoint || 'Track the condition most likely to invalidate the recommendation and schedule a formal review.',
      owner: 'Strategy & finance',
      state: 'Ongoing'
    })
  }

  return steps.slice(0, 3)
}
