import assert from 'node:assert/strict'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const fromFrontend = path => resolve(frontendRoot, path)

const v2Module = () => import(pathToFileURL(fromFrontend('src/demo/handlers/v2.js')).href)
const clockModule = () => import(pathToFileURL(fromFrontend('src/demo/clock.js')).href)
const statesModule = () => import(pathToFileURL(fromFrontend('src/demo/fixtures/v2/index.js')).href)

const findRoute = (routes, method, url) =>
  routes.find(route => route.method === method && route.pattern.test(url))

test('v2 fixtures: captured states form a coherent decision journey', async () => {
  const { v2States } = await statesModule()

  assert.equal(v2States.length, 9)
  for (const state of v2States) {
    assert.ok(state.run_id, 'every state has a run_id')
    assert.equal(state.run_type, 'internal')
    assert.equal(state.core_lineage.initial_report_id, 'report_demo_ycagi')
    assert.equal(state.core_lineage.project_id, 'proj_demo_ycagi')
    assert.equal(state.case_title, 'Y Combinator — AGI-Era Batch Strategy')
  }

  const first = v2States[0]
  assert.ok(first.internal_questions.some(q => q.status === 'requested'))
  assert.equal(first.decision_completion.final_approval_ready, false)
  assert.equal(first.contradictions[0].status, 'open')

  // Four answers accumulate one internal-evidence entry each.
  for (let i = 1; i <= 4; i++) {
    assert.equal(v2States[i].internal_evidence.length, i, `state ${i} has ${i} evidence entries`)
  }

  const afterAnswers = v2States[4]
  assert.equal(afterAnswers.decision_completion.internal_evidence_complete, true)
  assert.equal(afterAnswers.contradictions[0].status, 'resolved')

  assert.ok(v2States[5].decision_model_proposal, 'proposal attached after action confirmation')

  const afterModel = v2States[6]
  assert.equal(afterModel.decision_analysis_result.status, 'calculated')
  assert.equal(afterModel.decision_analysis_result.recommended_action, 'hypothesis_stage')

  const final = v2States[7]
  assert.equal(final.decision_completion.final_approval_ready, true)
  assert.equal(final.report.status, 'final')
  assert.match(final.report.recommendation, /Stage a reversible AGI-native track pilot/)
})

test('v2 handlers: mutations advance the state pointer, reads do not', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { routes } = await v2Module()
  const { v2States } = await statesModule()

  const get = findRoute(routes, 'get', '/api/v2/runs/run_x')
  const refinement = findRoute(routes, 'get', '/api/v2/core/reports/report_demo_ycagi/refinement')
  const answers = findRoute(routes, 'post', '/api/v2/runs/run_x/answers')
  const confirmActions = findRoute(routes, 'post', '/api/v2/runs/run_x/actions/confirm')
  const confirmModel = findRoute(routes, 'post', '/api/v2/runs/run_x/decision-model/confirm')
  const owners = findRoute(routes, 'post', '/api/v2/runs/run_x/execution-owners')
  const stop = findRoute(routes, 'post', '/api/v2/runs/run_x/stop/evaluate')

  assert.ok(get && refinement && answers && confirmActions && confirmModel && owners && stop)

  assert.equal(refinement.handler({}), v2States[0])
  assert.equal(get.handler({}), v2States[0])

  assert.equal(answers.handler({}), v2States[1])
  assert.equal(answers.handler({}), v2States[2])
  assert.equal(answers.handler({}), v2States[3])
  assert.equal(answers.handler({}), v2States[4])
  assert.equal(get.handler({}), v2States[4])

  assert.equal(confirmActions.handler({}).run, v2States[5])

  const confirmed = confirmModel.handler({})
  assert.equal(confirmed.run, v2States[6])
  assert.equal(confirmed.analysis.status, 'calculated')

  assert.equal(owners.handler({}).run, v2States[7])
  assert.equal(stop.handler({}), v2States[8])
  assert.equal(stop.handler({}), v2States[8]) // clamps at the last state
  assert.equal(get.handler({}), v2States[8])

  clock.__testHooks.reset()
})

test('v2 handlers: fork returns the current internal state with a 201', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { routes } = await v2Module()
  const { v2States } = await statesModule()

  const fork = findRoute(routes, 'post', '/api/v2/runs/run_x/fork')
  const result = fork.handler({})
  assert.equal(result.__status, 201)
  assert.equal(result.data, v2States[0])

  clock.__testHooks.reset()
})
