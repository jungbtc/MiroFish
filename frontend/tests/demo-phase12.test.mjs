import assert from 'node:assert/strict'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const fromFrontend = path => resolve(frontendRoot, path)

const phase12Module = () => import(pathToFileURL(fromFrontend('src/demo/handlers/phase12.js')).href)
const clockModule = () => import(pathToFileURL(fromFrontend('src/demo/clock.js')).href)
const timingsModule = () => import(pathToFileURL(fromFrontend('src/demo/timings.js')).href)

// Invokes a route handler directly (bypassing the adapter's simulated
// latency/envelope) so tests stay fast and deterministic, per the route
// contract documented in src/demo/adapter.js.
const call = (routes, method, url, { query = {}, body } = {}) => {
  const path = url.split('?')[0]
  const route = routes.find(r => r.method === method && r.pattern.test(path))
  assert.ok(route, `no demo route matched ${method.toUpperCase()} ${url}`)
  const match = route.pattern.exec(path)
  const params = match?.groups || {}
  return route.handler({ params, query, body, config: {} })
}

test('graph build task: polling at 0%, 50%, and 100% reports the correct stage and status', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  const { GRAPH_BUILD_SECONDS } = await timingsModule()
  clock.__testHooks.reset()

  const startedAt = 1_000_000
  let now = startedAt
  clock.__testHooks.setNow(() => now)
  clock.startJob('ontology') // in-flow session: keep live scripted progressions

  const build = await call(routes, 'post', '/api/graph/build', { body: { project_id: 'proj_demo_ycagi' } })
  assert.equal(build.task_id, 'task_demo_build')

  // 0%
  let task = await call(routes, 'get', '/api/graph/task/task_demo_build')
  assert.equal(task.status, 'processing')
  assert.equal(task.progress, 0)
  assert.equal(task.progress_detail.current_stage, 'extracting_entities')
  assert.equal(task.progress_detail.stage_index, 1)
  assert.equal(task.result, null)

  // 50%
  now = startedAt + Math.round(0.5 * GRAPH_BUILD_SECONDS * 1000)
  task = await call(routes, 'get', '/api/graph/task/task_demo_build')
  assert.equal(task.status, 'processing')
  assert.equal(task.progress, 50)
  assert.equal(task.progress_detail.current_stage, 'resolving_relations')

  // 100%
  now = startedAt + GRAPH_BUILD_SECONDS * 1000
  task = await call(routes, 'get', '/api/graph/task/task_demo_build')
  assert.equal(task.status, 'completed')
  assert.equal(task.progress, 100)
  assert.equal(task.progress_detail.current_stage, 'indexing')
  assert.ok(task.result)
  assert.equal(task.result.project_id, 'proj_demo_ycagi')
  assert.equal(task.result.graph_id, 'graph_demo_ycagi')
  assert.ok(task.result.node_count > 0)
  assert.ok(task.result.edge_count > 0)

  clock.__testHooks.reset()
})

test('graph data reveals a growing subset with no dangling edges, then everything once built', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  const { GRAPH_BUILD_SECONDS } = await timingsModule()
  clock.__testHooks.reset()

  const startedAt = 2_000_000
  let now = startedAt
  clock.__testHooks.setNow(() => now)
  clock.startJob('ontology') // in-flow session: keep live scripted progressions

  await call(routes, 'post', '/api/graph/build', { body: {} })

  const assertNoDanglingEdges = data => {
    const ids = new Set(data.nodes.map(n => n.uuid))
    for (const edge of data.edges) {
      assert.ok(ids.has(edge.source_node_uuid), `edge ${edge.uuid} source not revealed`)
      assert.ok(ids.has(edge.target_node_uuid), `edge ${edge.uuid} target not revealed`)
    }
    assert.equal(data.node_count, data.nodes.length)
    assert.equal(data.edge_count, data.edges.length)
  }

  // ~20% through the build: a strict subset should be revealed
  now = startedAt + Math.round(0.2 * GRAPH_BUILD_SECONDS * 1000)
  let data = await call(routes, 'get', '/api/graph/data/graph_demo_ycagi')
  assert.ok(data.nodes.length > 0)
  assert.ok(data.nodes.length < 42, 'expected a strict subset of nodes at 20% progress')
  assertNoDanglingEdges(data)
  const countAt20 = data.nodes.length

  // ~60% through the build: more nodes revealed than before
  now = startedAt + Math.round(0.6 * GRAPH_BUILD_SECONDS * 1000)
  data = await call(routes, 'get', '/api/graph/data/graph_demo_ycagi')
  assert.ok(data.nodes.length >= countAt20)
  assertNoDanglingEdges(data)

  // Fully built: everything is revealed
  now = startedAt + GRAPH_BUILD_SECONDS * 1000
  data = await call(routes, 'get', '/api/graph/data/graph_demo_ycagi')
  assert.equal(data.nodes.length, 42)
  assert.equal(data.edges.length, 71)
  assertNoDanglingEdges(data)

  clock.__testHooks.reset()
})

test('prepare status walks the four exact stage names Step2EnvSetup.vue string-matches', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  const { PREPARE_SECONDS } = await timingsModule()
  clock.__testHooks.reset()

  const startedAt = 3_000_000
  let now = startedAt
  clock.__testHooks.setNow(() => now)
  clock.startJob('ontology') // in-flow session: keep live scripted progressions

  const prepare = await call(routes, 'post', '/api/simulation/prepare', { body: { simulation_id: 'sim_demo_ycagi' } })
  assert.equal(prepare.already_prepared, false)
  assert.equal(prepare.task_id, 'task_demo_prepare')
  assert.equal(prepare.expected_entities_count, 16)
  assert.ok(prepare.entity_types.length > 0)

  const stageNameAt = fraction => {
    now = startedAt + Math.round(fraction * PREPARE_SECONDS * 1000)
    return call(routes, 'post', '/api/simulation/prepare/status', { body: { task_id: 'task_demo_prepare', simulation_id: 'sim_demo_ycagi' } })
  }

  assert.equal((await stageNameAt(0)).progress_detail.current_stage_name, 'analyzing_entities')
  assert.equal((await stageNameAt(0.4)).progress_detail.current_stage_name, 'generating_profiles')
  assert.equal((await stageNameAt(0.8)).progress_detail.current_stage_name, 'generating_config')
  assert.equal((await stageNameAt(0.95)).progress_detail.current_stage_name, 'copying_scripts')

  const completed = await stageNameAt(1)
  assert.equal(completed.status, 'completed')
  assert.equal(completed.already_prepared, true)

  clock.__testHooks.reset()
})

test('profiles/realtime count grows across the generating_profiles window then holds at 16', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  const { PREPARE_SECONDS } = await timingsModule()
  clock.__testHooks.reset()

  const startedAt = 4_000_000
  let now = startedAt
  clock.__testHooks.setNow(() => now)
  clock.startJob('ontology') // in-flow session: keep live scripted progressions

  await call(routes, 'post', '/api/simulation/prepare', { body: { simulation_id: 'sim_demo_ycagi' } })

  const countAt = async fraction => {
    now = startedAt + Math.round(fraction * PREPARE_SECONDS * 1000)
    const res = await call(routes, 'get', '/api/simulation/sim_demo_ycagi/profiles/realtime', { query: { platform: 'reddit' } })
    assert.equal(res.total_expected, 16)
    return res.profiles.length
  }

  assert.equal(await countAt(0), 0) // before the generating_profiles window starts
  const mid = await countAt(0.15 + 0.55 * 0.5) // midway through the window
  assert.ok(mid > 0 && mid < 16, `expected a partial reveal midway, got ${mid}`)
  assert.equal(await countAt(0.70), 16) // window fully elapsed
  assert.equal(await countAt(1), 16) // stays at 16 afterward

  clock.__testHooks.reset()
})

test('config/realtime flips config_generated exactly at the 0.90 boundary', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  const { PREPARE_SECONDS } = await timingsModule()
  clock.__testHooks.reset()

  const startedAt = 5_000_000
  let now = startedAt
  clock.__testHooks.setNow(() => now)
  clock.startJob('ontology') // in-flow session: keep live scripted progressions

  await call(routes, 'post', '/api/simulation/prepare', { body: { simulation_id: 'sim_demo_ycagi' } })

  const configAt = fraction => {
    now = startedAt + Math.round(fraction * PREPARE_SECONDS * 1000)
    return call(routes, 'get', '/api/simulation/sim_demo_ycagi/config/realtime')
  }

  let res = await configAt(0.3)
  assert.equal(res.generation_stage, 'waiting_for_profiles')
  assert.equal(res.config_generated, false)

  res = await configAt(0.8)
  assert.equal(res.generation_stage, 'generating')
  assert.equal(res.config_generated, false)

  res = await configAt(0.9)
  assert.equal(res.generation_stage, 'completed')
  assert.equal(res.config_generated, true)
  assert.ok(res.config)
  assert.equal(res.config.time_config.minutes_per_round, 30)
  assert.equal(res.summary.total_agents, 16)
  assert.equal(res.summary.has_twitter_config, true)
  assert.equal(res.summary.has_reddit_config, true)

  clock.__testHooks.reset()
})

test('simulation history returns the completed YC entry and an in-progress decoy', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  clock.__testHooks.reset()

  const history = await call(routes, 'get', '/api/simulation/history', { query: { limit: 20 } })
  assert.equal(history.length, 2)

  const completed = history.find(h => h.simulation_id === 'sim_demo_ycagi')
  assert.ok(completed)
  assert.equal(completed.project_id, 'proj_demo_ycagi')
  assert.equal(completed.report_id, 'report_demo_ycagi')
  assert.equal(completed.current_round, 10)
  assert.equal(completed.total_rounds, 10)
  assert.equal(completed.files.length, 3)

  const inProgress = history.find(h => h.simulation_id !== 'sim_demo_ycagi')
  assert.ok(inProgress)
  assert.ok(!inProgress.report_id)
  assert.ok(inProgress.current_round < inProgress.total_rounds)
})

test('simulation/:id status reflects the prepare job: created before, prepared after (never running)', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  const { PREPARE_SECONDS } = await timingsModule()
  clock.__testHooks.reset()

  const startedAt = 6_000_000
  let now = startedAt
  clock.__testHooks.setNow(() => now)
  clock.startJob('ontology') // in-flow session: keep live scripted progressions

  let sim = await call(routes, 'get', '/api/simulation/sim_demo_ycagi')
  assert.equal(sim.status, 'created')

  await call(routes, 'post', '/api/simulation/prepare', { body: { simulation_id: 'sim_demo_ycagi' } })

  now = startedAt + Math.round(0.5 * PREPARE_SECONDS * 1000)
  sim = await call(routes, 'get', '/api/simulation/sim_demo_ycagi')
  assert.equal(sim.status, 'created')

  now = startedAt + PREPARE_SECONDS * 1000
  sim = await call(routes, 'get', '/api/simulation/sim_demo_ycagi')
  assert.equal(sim.status, 'prepared')
  assert.notEqual(sim.status, 'running')

  clock.__testHooks.reset()
})

test('project status derives from the graphBuild clock job (MainView.vue:258-266 status strings)', async () => {
  const { routes } = await phase12Module()
  const clock = await clockModule()
  const { GRAPH_BUILD_SECONDS } = await timingsModule()
  clock.__testHooks.reset()

  const startedAt = 7_000_000
  let now = startedAt
  clock.__testHooks.setNow(() => now)
  clock.startJob('ontology') // in-flow session: keep live scripted progressions

  let project = await call(routes, 'get', '/api/graph/project/proj_demo_ycagi')
  assert.equal(project.status, 'ontology_generated')
  assert.equal(project.graph_id, 'graph_demo_ycagi')

  await call(routes, 'post', '/api/graph/build', { body: {} })

  now = startedAt + Math.round(0.5 * GRAPH_BUILD_SECONDS * 1000)
  project = await call(routes, 'get', '/api/graph/project/proj_demo_ycagi')
  assert.equal(project.status, 'graph_building')
  assert.equal(project.graph_build_task_id, 'task_demo_build')

  now = startedAt + GRAPH_BUILD_SECONDS * 1000
  project = await call(routes, 'get', '/api/graph/project/proj_demo_ycagi')
  assert.equal(project.status, 'graph_completed')

  clock.__testHooks.reset()
})
