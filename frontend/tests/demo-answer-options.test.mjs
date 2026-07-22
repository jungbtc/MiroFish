import assert from 'node:assert/strict'
import test from 'node:test'

import ANSWER_OPTION_SETS, { findAnswerOptions } from '../src/demo/fixtures/answerOptions.js'
import { v2States } from '../src/demo/fixtures/v2/index.js'

const optionsFor = id => ANSWER_OPTION_SETS.find(set => set.id === id).options

const questionTextFor = (state, category) => {
  const question = state.internal_questions.find(q => q.category === category)
  assert.ok(question, `state has an internal question in category "${category}"`)
  return question.question
}

test('every answer-option set has exactly 3 well-formed options', () => {
  assert.equal(ANSWER_OPTION_SETS.length, 5, 'four question sets + one generic fallback')

  for (const set of ANSWER_OPTION_SETS) {
    assert.equal(set.options.length, 3, `set "${set.id}" has exactly 3 options`)
    for (const option of set.options) {
      assert.ok(typeof option.title === 'string' && option.title.trim().length > 0, `${set.id} option has a non-empty title`)
      assert.ok(typeof option.text === 'string' && option.text.trim().length > 0, `${set.id} option has non-empty text`)
      assert.ok(
        typeof option.submitted_by === 'string' && option.submitted_by.trim().length > 0,
        `${set.id} option has a non-empty submitted_by`
      )
      assert.ok(typeof option.confidence === 'number' && option.confidence > 0 && option.confidence <= 1, `${set.id} option has a plausible confidence`)
    }
  }
})

// The four internal questions (and their category labels) are stable across
// states 0-3 in the captured v2 fixtures — only status/answer_id/scores change.
test('the four real internal questions route to their intended answer set across states 0-3', () => {
  for (let i = 0; i <= 3; i++) {
    const state = v2States[i]

    const constraintsQuestion = questionTextFor(state, 'constraints')
    const outcomeQuestion = questionTextFor(state, 'strategic_success')
    const budgetQuestion = questionTextFor(state, 'financial_capacity')
    const downsideQuestion = questionTextFor(state, 'risk_tolerance')

    assert.equal(
      findAnswerOptions(constraintsQuestion),
      optionsFor('constraints'),
      `state ${i}: constraints question ("${constraintsQuestion}") routes to the constraints set`
    )
    assert.equal(
      findAnswerOptions(outcomeQuestion),
      optionsFor('outcome'),
      `state ${i}: strategic-success question ("${outcomeQuestion}") routes to the outcome set, not the downside/regret set (it also contains the word "outcome")`
    )
    assert.equal(
      findAnswerOptions(budgetQuestion),
      optionsFor('budget'),
      `state ${i}: financial-capacity question ("${budgetQuestion}") routes to the budget set, not the downside/regret set (it also contains the word "downside")`
    )
    assert.equal(
      findAnswerOptions(downsideQuestion),
      optionsFor('downside'),
      `state ${i}: risk-tolerance question ("${downsideQuestion}") routes to the downside set`
    )
  }
})

test('findAnswerOptions falls back to the generic set for unmatched questions', () => {
  assert.equal(findAnswerOptions('What is the current weather forecast?'), optionsFor('generic'))
  assert.equal(findAnswerOptions(''), optionsFor('generic'))
  assert.equal(findAnswerOptions(undefined), optionsFor('generic'))
})

test('answer options carry the canonical option-1 text for each real question', () => {
  const state = v2States[0]

  assert.equal(
    findAnswerOptions(questionTextFor(state, 'constraints'))[0].text,
    "There is no non-negotiable legal or policy blocker. YC's equal-access admissions policy requires the AGI-Native Track to remain open to every applicant profile, and two LP side letters require 60-day notice before any permanent batch-model change, but a time-limited reversible track pilot is expressly permitted."
  )
  assert.equal(
    findAnswerOptions(questionTextFor(state, 'strategic_success'))[0].text,
    "The pilot must show AGI-native track companies reaching at least 1.6 times the classic batch's median week-12 release velocity with an incident rate no higher than 1.2 times baseline, and all 60 pilot slots filled by qualified applicants; minimum acceptable outcome is quality parity with the classic batch."
  )
  assert.equal(
    findAnswerOptions(questionTextFor(state, 'financial_capacity'))[0].text,
    'The partnership approved a binding $25 million pilot allocation from the standard fund for the first AGI-Native Track cohort, with a dedicated staff of 6 partners and program managers covering both pilot cohorts through 2027-06-30. Elena Voss (Group Partner) is the named full-time track owner accountable for the pilot, and Marcus Oyelaran (Managing Partner) is the approver for expansion gates.'
  )
  assert.equal(
    findAnswerOptions(questionTextFor(state, 'risk_tolerance'))[0].text,
    'Leadership would regret the decision if it damaged the YC brand or LP alignment: the approved downside limit is the $25 million pilot exposure, an incident rate no higher than 1.5 times baseline, and zero breaches of the equal-access policy. Roughly 40% of expected pilot value depends on avoiding those outcomes.'
  )
})
