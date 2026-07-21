import assert from 'node:assert/strict'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const fromFrontend = path => resolve(frontendRoot, path)

const adapterModule = () => import(pathToFileURL(fromFrontend('src/demo/adapter.js')).href)
const clockModule = () => import(pathToFileURL(fromFrontend('src/demo/clock.js')).href)
const timingsModule = () => import(pathToFileURL(fromFrontend('src/demo/timings.js')).href)
const routesModule = () => import(pathToFileURL(fromFrontend('src/demo/handlers/phase345.js')).href)
const actionsModule = () => import(pathToFileURL(fromFrontend('src/demo/fixtures/actions.js')).href)
const agentLogModule = () => import(pathToFileURL(fromFrontend('src/demo/fixtures/agentLog.js')).href)
const scenarioModule = () => import(pathToFileURL(fromFrontend('src/demo/fixtures/scenario.js')).href)

const buildAdapter = async () => {
  const { createDemoAdapter } = await adapterModule()
  const { routes } = await routesModule()
  return createDemoAdapter(routes)
}

test('simulation run-status derives round/counts from elapsed fraction and completes at f=1', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { RUN_SECONDS } = await timingsModule()
  const { default: actions } = await actionsModule()
  const { IDS } = await scenarioModule()

  let now = 1_000_000
  clock.__testHooks.setNow(() => now)

  const adapter = await buildAdapter()

  const startRes = await adapter({
    method: 'post',
    url: '/api/simulation/start',
    data: JSON.stringify({ simulation_id: IDS.simulationId })
  })
  assert.equal(startRes.data.data.runner_status, 'running')
  assert.equal(startRes.data.data.twitter_current_round, 0)

  now += RUN_SECONDS * 0.5 * 1000 // f = 0.5 -> round 5
  const midRes = await adapter({
    method: 'get',
    url: `/api/simulation/${IDS.simulationId}/run-status`
  })
  const mid = midRes.data.data
  assert.equal(mid.runner_status, 'running')
  assert.equal(mid.twitter_current_round, 5)
  assert.equal(mid.reddit_current_round, 5)
  assert.equal(mid.twitter_running, true)
  assert.equal(mid.reddit_completed, false)

  const expectedTwitter = actions.filter(a => a.platform === 'twitter' && a.round_num <= 5).length
  const expectedReddit = actions.filter(a => a.platform === 'reddit' && a.round_num <= 5).length
  assert.equal(mid.twitter_actions_count, expectedTwitter)
  assert.equal(mid.reddit_actions_count, expectedReddit)
  assert.equal(mid.total_actions_count, expectedTwitter + expectedReddit)

  now += RUN_SECONDS * 0.5 * 1000 // f = 1.0 -> round 10, completed
  const doneRes = await adapter({
    method: 'get',
    url: `/api/simulation/${IDS.simulationId}/run-status`
  })
  const done = doneRes.data.data
  assert.equal(done.runner_status, 'completed')
  assert.equal(done.twitter_current_round, 10)
  assert.equal(done.twitter_completed, true)
  assert.equal(done.reddit_completed, true)
  assert.equal(done.twitter_running, false)
  assert.equal(done.reddit_running, false)

  clock.__testHooks.reset()
})

test('run-status/detail never returns actions from a future round', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { RUN_SECONDS } = await timingsModule()
  const { IDS } = await scenarioModule()

  let now = 3_000_000
  clock.__testHooks.setNow(() => now)

  const adapter = await buildAdapter()
  await adapter({ method: 'post', url: '/api/simulation/start', data: JSON.stringify({ simulation_id: IDS.simulationId }) })

  now += RUN_SECONDS * 0.3 * 1000 // f = 0.3 -> round 3
  const detailRes = await adapter({
    method: 'get',
    url: `/api/simulation/${IDS.simulationId}/run-status/detail`
  })
  const detail = detailRes.data.data

  assert.equal(detail.rounds_count, 3)
  assert.ok(detail.all_actions.length > 0)
  assert.ok(detail.all_actions.every(a => a.round_num <= 3))

  clock.__testHooks.reset()
})

test('agent-log delivers an incremental prefix via from_line and finishes with report_complete', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { REPORT_SECONDS } = await timingsModule()
  const { default: fullAgentLog } = await agentLogModule()
  const { IDS } = await scenarioModule()

  // Fixture sanity: every timestamp must be unique (used as a Vue :key).
  const uniqueTimestamps = new Set(fullAgentLog.map(entry => entry.timestamp))
  assert.equal(uniqueTimestamps.size, fullAgentLog.length)
  // And strictly increasing `at` fractions.
  for (let i = 1; i < fullAgentLog.length; i += 1) {
    assert.ok(fullAgentLog[i].at > fullAgentLog[i - 1].at)
  }

  let now = 5_000_000
  clock.__testHooks.setNow(() => now)

  const adapter = await buildAdapter()
  await adapter({ method: 'post', url: '/api/report/generate', data: JSON.stringify({ simulation_id: IDS.simulationId }) })

  now += REPORT_SECONDS * 0.3 * 1000 // f = 0.3
  const firstRes = await adapter({
    method: 'get',
    url: `/api/report/${IDS.reportId}/agent-log`,
    params: { from_line: 0 }
  })
  const firstLogs = firstRes.data.data.logs
  assert.ok(firstLogs.length > 0)
  assert.ok(firstLogs.length < fullAgentLog.length, 'f=0.3 should only reveal a prefix, not the whole log')
  // The internal `at` bookkeeping field must not leak through the API.
  assert.ok(firstLogs.every(entry => !('at' in entry)))

  const consumedAfterFirst = firstRes.data.data.from_line + firstLogs.length

  now += REPORT_SECONDS * 0.3 * 1000 // f = 0.6
  const secondRes = await adapter({
    method: 'get',
    url: `/api/report/${IDS.reportId}/agent-log`,
    params: { from_line: consumedAfterFirst }
  })
  const secondLogs = secondRes.data.data.logs
  assert.ok(secondLogs.length > 0, 'advancing time should reveal more entries')

  // No overlap: combined prefix must equal exactly what's visible at f=0.6.
  const combinedActions = [...firstLogs, ...secondLogs].map(entry => entry.action)
  const expectedAtSixty = fullAgentLog.filter(entry => entry.at <= 0.6).map(entry => entry.action)
  assert.deepEqual(combinedActions, expectedAtSixty)

  const consumedAfterSecond = secondRes.data.data.from_line + secondLogs.length

  now += REPORT_SECONDS * 1.0 * 1000 // f = 1.0 -> everything visible
  const finalRes = await adapter({
    method: 'get',
    url: `/api/report/${IDS.reportId}/agent-log`,
    params: { from_line: consumedAfterSecond }
  })
  const finalLogs = finalRes.data.data.logs
  const allDelivered = [...firstLogs, ...secondLogs, ...finalLogs]
  assert.equal(allDelivered.length, fullAgentLog.length)
  assert.equal(allDelivered[allDelivered.length - 1].action, 'report_complete')

  clock.__testHooks.reset()
})

test('interview batch returns a reddit_<agent_id> keyed persona reply per requested agent', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { IDS } = await scenarioModule()

  const adapter = await buildAdapter()
  const res = await adapter({
    method: 'post',
    url: '/api/simulation/interview/batch',
    data: JSON.stringify({
      simulation_id: IDS.simulationId,
      interviews: [
        { agent_id: 0, prompt: 'How do you see this playing out?' },
        { agent_id: 6, prompt: 'Does the pilot satisfy the union?' }
      ]
    })
  })

  const results = res.data.data.result.results
  assert.ok('reddit_0' in results)
  assert.ok('reddit_6' in results)
  assert.equal(typeof results.reddit_0.response, 'string')
  assert.ok(results.reddit_0.response.length > 0)
  assert.notEqual(results.reddit_0.response, results.reddit_6.response)

  clock.__testHooks.reset()
})

test('GET /api/report/:id resolves without a simulation_id mismatch', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { IDS } = await scenarioModule()

  const adapter = await buildAdapter()
  const res = await adapter({ method: 'get', url: `/api/report/${IDS.reportId}` })

  assert.equal(res.data.data.report_id, IDS.reportId)
  assert.equal(res.data.data.simulation_id, IDS.simulationId)
  assert.equal(res.data.data.status, 'completed')

  clock.__testHooks.reset()
})
