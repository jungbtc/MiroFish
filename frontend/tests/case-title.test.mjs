import assert from 'node:assert/strict'
import test from 'node:test'

import { summarizeCaseTitle } from '../src/utils/caseTitle.js'

test('keeps an explicit concise case title unchanged', () => {
  assert.equal(
    summarizeCaseTitle('Samsung HBM4 capacity strategy', 'A much longer question'),
    'Samsung HBM4 capacity strategy'
  )
})

test('turns a legacy full simulation prompt into a scannable decision title', () => {
  const prompt = 'We have just reported record Q2 2026 operating profit. Simulate what would happen if Samsung Electronics announces that it will aggressively expand HBM4 and advanced-packaging capacity only where demand is backed by long-term customer commitments, while refusing a broad price war. Model reactions and outcomes over 3, 6, and 12 months.'

  assert.equal(
    summarizeCaseTitle(prompt, prompt),
    'Samsung Electronics · HBM4 capacity strategy'
  )
})

test('prefers the simulated intervention over an earlier market uncertainty clause', () => {
  const prompt = 'We have just reported record Q2 2026 operating profit, but the market remains skeptical about whether this represents durable HBM leadership or the peak of another memory cycle. Simulate what would happen if Samsung Electronics announces that it will aggressively expand HBM4 and advanced-packaging capacity only where demand is backed by long-term customer commitments, while refusing a broad price war. Model reactions.'

  assert.equal(
    summarizeCaseTitle(prompt, prompt),
    'Samsung Electronics · HBM4 capacity strategy'
  )
})

test('bounds generic legacy titles even without recognizable entities', () => {
  const prompt = 'Should the organization enter the market now with a focused offer for its best customers before competitors respond and operating costs rise materially over the coming year?'
  assert.ok(summarizeCaseTitle(prompt, prompt).length < prompt.length)
})
