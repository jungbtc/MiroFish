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

  assert.equal(v2States.length, 6)
  for (const state of v2States) {
    assert.ok(state.run_id, 'every state has a run_id')
    assert.equal(state.run_type, 'internal')
    assert.equal(state.core_lineage.initial_report_id, 'report_demo_northstar')
    assert.equal(state.core_lineage.project_id, 'proj_demo_northstar')
  }

  const first = v2States[0]
  assert.ok(first.internal_questions.some(q => q.status === 'requested'))
  assert.equal(first.decision_completion.final_approval_ready, false)

  const afterModel = v2States[3]
  assert.equal(afterModel.decision_analysis_result.status, 'calculated')

  const final = v2States[4]
  assert.equal(final.decision_completion.final_approval_ready, true)
  assert.equal(final.report.status, 'final')
})

test('v2 handlers: mutations advance the state pointer, reads do not', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { routes } = await v2Module()
  const { v2States } = await statesModule()

  const get = findRoute(routes, 'get', '/api/v2/runs/run_x')
  const refinement = findRoute(routes, 'get', '/api/v2/core/reports/report_demo_northstar/refinement')
  const answers = findRoute(routes, 'post', '/api/v2/runs/run_x/answers')
  const confirmActions = findRoute(routes, 'post', '/api/v2/runs/run_x/actions/confirm')
  const confirmModel = findRoute(routes, 'post', '/api/v2/runs/run_x/decision-model/confirm')
  const owners = findRoute(routes, 'post', '/api/v2/runs/run_x/execution-owners')
  const stop = findRoute(routes, 'post', '/api/v2/runs/run_x/stop/evaluate')

  assert.ok(get && refinement && answers && confirmActions && confirmModel && owners && stop)

  assert.equal(refinement.handler({}), v2States[0])
  assert.equal(get.handler({}), v2States[0])

  assert.equal(answers.handler({}), v2States[1])
  assert.equal(get.handler({}), v2States[1])

  assert.equal(confirmActions.handler({}).run, v2States[2])

  const confirmed = confirmModel.handler({})
  assert.equal(confirmed.run, v2States[3])
  assert.equal(confirmed.analysis.status, 'calculated')

  assert.equal(owners.handler({}).run, v2States[4])
  assert.equal(owners.handler({}).run, v2States[5]) // clamps at the last state afterwards
  assert.equal(owners.handler({}).run, v2States[5])

  assert.equal(stop.handler({}), v2States[5]) // read-back, no advance
  assert.equal(get.handler({}), v2States[5])

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
