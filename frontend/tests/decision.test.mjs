import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildExecutiveActionPlan,
  branchTone,
  evidencePosture,
  formatDelta,
  formatScore,
  hypothesisDelta,
  looksLikeExecutableAction,
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

test('final decisions reject market observations and accept executable actions', () => {
  assert.equal(looksLikeExecutableAction('Driven largely by AI-memory demand'), false)
  assert.equal(looksLikeExecutableAction('The market remains skeptical about the cycle'), false)
  assert.equal(looksLikeExecutableAction('Select Store managers'), false)
  assert.equal(looksLikeExecutableAction('Recommend Non-members'), false)
  assert.equal(looksLikeExecutableAction('Run a smaller, controlled pilot'), true)
  assert.equal(looksLikeExecutableAction('Redesign the benefit before launch'), true)
  assert.equal(looksLikeExecutableAction('Commitment-gated HBM4 and packaging expansion'), true)
  assert.equal(looksLikeExecutableAction('Approve Phase 1 capacity expansion'), true)
})

test('evidence posture reports evidence completion separately from approval gates', () => {
  assert.equal(evidencePosture({ sourcedClaims: 12, internalEvidenceComplete: true, isFinal: false, actionIsExecutable: true }), 'Internal evidence complete')
  assert.equal(evidencePosture({ sourcedClaims: 1, isFinal: true, actionIsExecutable: true }), 'Conditional')
  assert.equal(evidencePosture({ sourcedClaims: 4, isFinal: true, actionIsExecutable: true }), 'Decision-ready')
})

test('executive action plan begins with approval and includes open decision gates', () => {
  const plan = buildExecutiveActionPlan({
    recommendedAction: 'Approve Phase 1 HBM4 expansion',
    actionIsExecutable: true,
    actionsConfirmed: true,
    isReady: false,
    openQuestions: [{
      question: 'What committed volume is secured?',
      expected_change: 'Determines the safe first tranche.',
      owner_hint: 'Commercial lead'
    }]
  })

  assert.equal(plan.length, 3)
  assert.match(plan[0].title, /^Prepare:/)
  assert.equal(plan[1].owner, 'Commercial lead')
  assert.equal(plan[1].state, 'Open')
})

test('unconfirmed action sets stay at the management action gate', () => {
  const plan = buildExecutiveActionPlan({
    recommendedAction: 'Run a constrained 50-store pilot',
    actionIsExecutable: true,
    actionsConfirmed: false,
    isReady: false,
    openQuestions: []
  })

  assert.equal(plan[0].title, 'Confirm the management action set')
  assert.equal(plan[0].state, 'Required')
})
