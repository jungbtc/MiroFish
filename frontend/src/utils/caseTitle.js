const toPlainText = value => String(value || '')
  .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
  .replace(/[*_`#>]/g, '')
  .replace(/\s+/g, ' ')
  .trim()

/**
 * Keeps a decision case scannable when older run records use the entire
 * simulation prompt as their title. New records should still provide a
 * concise `case_title`; this is a deterministic display fallback only.
 */
export const summarizeCaseTitle = (preferredTitle, question = '') => {
  const preferred = toPlainText(preferredTitle)
  if (preferred && preferred.length <= 96) return preferred

  const source = toPlainText(question || preferred)
  // Prefer the explicit intervention clause. Long prompts often mention an
  // earlier market uncertainty ("whether this represents...") before the
  // actual "what would happen if..." decision being simulated.
  const decisionClause = source.match(/what (?:would|will) happen if\s+(.+?)(?:\.|\bwhile\b|\bModel\b|\bShow\b|\bDetermine\b|\bIdentify\b)/i)?.[1]
    || source.match(/whether\s+(.+?)(?:\.|\bwhile\b|\bModel\b|\bShow\b|\bDetermine\b|\bIdentify\b)/i)?.[1]
    || source.match(/(?:should|if)\s+(.+?)(?:\.|\bwhile\b)/i)?.[1]
    || source
  const cleaned = decisionClause
    .replace(/\bannounces? that (?:it|they) will\b/i, '')
    .replace(/\bwe have (?:just )?/i, '')
    .replace(/\s+/g, ' ')
    .trim()

  const subject = cleaned.match(/^([A-Z][\w&.-]+(?:\s+[A-Z][\w&.-]+){0,2})\b/)?.[1]
  const keyTerms = [...cleaned.matchAll(/\b(?:[A-Z]{2,}\d*|[A-Za-z]+\d+[A-Za-z0-9-]*)\b/g)]
    .map(match => match[0])
    .filter(term => !['AI', 'Q1', 'Q2', 'Q3', 'Q4'].includes(term))

  if (subject && keyTerms.length) {
    const topic = [...new Set(keyTerms)].slice(0, 2).join(' / ')
    const suffix = /expand|capacity|supply/i.test(cleaned) ? 'capacity strategy' : 'decision scenario'
    return `${subject} · ${topic} ${suffix}`
  }

  const words = cleaned.split(' ').filter(Boolean)
  if (words.length > 14) return `${words.slice(0, 14).join(' ')}…`
  return cleaned || 'Decision refinement'
}
