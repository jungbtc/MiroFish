import assert from 'node:assert/strict'
import test from 'node:test'

import {
  branchTone,
  formatDelta,
  formatScore,
  hypothesisDelta,
  scorePercent
} from '../src/utils/decision.js'

test('normalizes fractional and percentage scores for decision meters', () => {
  assert.equal(scorePercent(0.73), 73)
  assert.equal(scorePercent(73), 73)
  assert.equal(formatScore(0.734), '73%')
  assert.equal(scorePercent(140), 100)
})

test('derives strengthened, weakened, and pruned branch states', () => {
  assert.equal(branchTone({ support_score: 0.7, previous_score: 0.5 }), 'strengthened')
  assert.equal(branchTone({ support_score: 0.4, previous_score: 0.6 }), 'weakened')
  assert.equal(branchTone({ status: 'pruned', last_change: 0.2 }), 'pruned')
  assert.equal(hypothesisDelta({ support_score: 0.4, previous_score: 0.6 }), -0.2)
})

test('formats score deltas as percentage-point changes', () => {
  assert.equal(formatDelta(0.125), '+12.5 pts')
  assert.equal(formatDelta(-8), '-8.0 pts')
  assert.equal(formatDelta(0), 'No change')
})
