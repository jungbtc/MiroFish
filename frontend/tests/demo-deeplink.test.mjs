import assert from 'node:assert/strict'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const fromFrontend = path => resolve(frontendRoot, path)

const clockModule = () => import(pathToFileURL(fromFrontend('src/demo/clock.js')).href)
const phase12Module = () => import(pathToFileURL(fromFrontend('src/demo/handlers/phase12.js')).href)
const phase345Module = () => import(pathToFileURL(fromFrontend('src/demo/handlers/phase345.js')).href)

const findRoute = (routes, method, url) =>
  routes.find(route => route.method === method && route.pattern.test(url))

// A fresh session that never went through the Home upload console (no
// 'ontology' job) must see every stage already completed — direct links to
// /process, /simulation and /simulation/:id/start were previously replaying
// their progressions from zero, showing broken graphs and empty action feeds.
test('deep link: project, graph, prepare and run all serve the completed state', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  const { routes: p12 } = await phase12Module()
  const { routes: p345 } = await phase345Module()

  const project = findRoute(p12, 'get', '/api/graph/project/proj_demo_ycagi').handler({ params: {} })
  assert.equal(project.status, 'graph_completed')

  const graph = findRoute(p12, 'get', '/api/graph/data/graph_demo_ycagi').handler({})
  assert.equal(graph.nodes.length, 42)
  assert.equal(graph.edges.length, 71)

  const profiles = findRoute(p12, 'get', '/api/simulation/sim_demo_ycagi/profiles/realtime').handler({ query: {} })
  assert.equal(profiles.profiles.length, 16)

  const config = findRoute(p12, 'get', '/api/simulation/sim_demo_ycagi/config/realtime').handler({})
  assert.equal(config.config_generated, true)

  const status = findRoute(p345, 'get', '/api/simulation/sim_demo_ycagi/run-status').handler({})
  assert.equal(status.runner_status, 'completed')
  assert.equal(status.twitter_current_round, 40)
  assert.equal(status.total_rounds, 40)

  const detail = findRoute(p345, 'get', '/api/simulation/sim_demo_ycagi/run-status/detail').handler({})
  assert.equal(detail.all_actions.length, 80)

  const agentLog = findRoute(p345, 'get', '/api/report/report_demo_ycagi/agent-log').handler({ query: { from_line: 0 } })
  assert.equal(agentLog.logs.at(-1).action, 'report_complete')

  clock.__testHooks.reset()
})

// The same handlers keep the live scripted progressions when the session
// entered through the Home flow (the ontology POST marks the session).
test('in-flow session: progressions still play out from zero', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()
  let now = 5_000_000
  clock.__testHooks.setNow(() => now)
  const { routes: p12 } = await phase12Module()

  findRoute(p12, 'post', '/api/graph/ontology/generate').handler({})
  findRoute(p12, 'post', '/api/graph/build').handler({ body: {} })
  const task = findRoute(p12, 'get', '/api/graph/task/task_demo_build').handler({ params: { taskId: 't' } })
  assert.equal(task.status, 'processing')
  assert.ok(task.progress < 100)

  clock.__testHooks.reset()
})
