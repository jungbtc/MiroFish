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
