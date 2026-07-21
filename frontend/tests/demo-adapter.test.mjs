import assert from 'node:assert/strict'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const fromFrontend = path => resolve(frontendRoot, path)

const adapterModule = () => import(pathToFileURL(fromFrontend('src/demo/adapter.js')).href)
const clockModule = () => import(pathToFileURL(fromFrontend('src/demo/clock.js')).href)

test('demo adapter: unmatched route returns a success envelope with empty data', async () => {
  const { createDemoAdapter } = await adapterModule()
  const adapter = createDemoAdapter([])

  const response = await adapter({ method: 'get', url: '/api/does-not-exist' })

  assert.equal(response.status, 200)
  assert.equal(response.statusText, 'OK')
  assert.deepEqual(response.data, { success: true, data: {} })
})

test('demo adapter: matched route extracts named params and wraps the result', async () => {
  const { createDemoAdapter } = await adapterModule()
  const routes = [
    {
      method: 'get',
      pattern: /^\/api\/graph\/task\/(?<taskId>[^/?]+)$/,
      latency: 0,
      handler: ({ params }) => ({ taskId: params.taskId, status: 'done' })
    }
  ]
  const adapter = createDemoAdapter(routes)

  const response = await adapter({ method: 'get', url: '/api/graph/task/abc123?x=1' })

  assert.equal(response.status, 200)
  assert.deepEqual(response.data, {
    success: true,
    data: { taskId: 'abc123', status: 'done' }
  })
})

test('demo adapter: responseType "text" bypasses the envelope', async () => {
  const { createDemoAdapter } = await adapterModule()
  const routes = [
    {
      method: 'get',
      pattern: /^\/api\/v2\/runs\/(?<runId>[^/?]+)\/report\.md$/,
      latency: 0,
      handler: ({ params }) => `# Memo for ${params.runId}`
    }
  ]
  const adapter = createDemoAdapter(routes)

  const response = await adapter({
    method: 'get',
    url: '/api/v2/runs/run_1/report.md',
    responseType: 'text'
  })

  assert.equal(response.data, '# Memo for run_1')
})

test('demo adapter: a handler can override the response status', async () => {
  const { createDemoAdapter } = await adapterModule()
  const routes = [
    {
      method: 'post',
      pattern: /^\/api\/graph\/build$/,
      latency: 0,
      handler: () => ({ __status: 201, data: { taskId: 'task_1' } })
    }
  ]
  const adapter = createDemoAdapter(routes)

  const response = await adapter({ method: 'post', url: '/api/graph/build', data: '{}' })

  assert.equal(response.status, 201)
  assert.deepEqual(response.data, { success: true, data: { taskId: 'task_1' } })
})

test('demo adapter: string request bodies are parsed as JSON before reaching the handler', async () => {
  const { createDemoAdapter } = await adapterModule()
  let receivedBody = null
  const routes = [
    {
      method: 'post',
      pattern: /^\/api\/simulation\/create$/,
      latency: 0,
      handler: ({ body }) => {
        receivedBody = body
        return { ok: true }
      }
    }
  ]
  const adapter = createDemoAdapter(routes)

  await adapter({ method: 'post', url: '/api/simulation/create', data: '{"project_id":"p1"}' })

  assert.deepEqual(receivedBody, { project_id: 'p1' })
})

test('clock: jobFraction is 0 and jobElapsed is null before a job starts', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()

  assert.equal(clock.jobStarted('graph_build'), false)
  assert.equal(clock.jobElapsed('graph_build'), null)
  assert.equal(clock.jobFraction('graph_build', 15), 0)

  clock.__testHooks.reset()
})

test('clock: fraction advances with injected time and clamps at 1, state persists across calls', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()

  let now = 1_000_000
  clock.__testHooks.setNow(() => now)

  clock.startJob('graph_build')
  assert.equal(clock.jobStarted('graph_build'), true)
  assert.equal(clock.jobFraction('graph_build', 10), 0)

  now += 5000
  assert.equal(clock.jobFraction('graph_build', 10), 0.5)

  // Starting again is a no-op once a job has begun.
  clock.startJob('graph_build')
  assert.equal(clock.jobFraction('graph_build', 10), 0.5)

  now += 20000
  assert.equal(clock.jobFraction('graph_build', 10), 1)

  clock.resetJob('graph_build')
  assert.equal(clock.jobStarted('graph_build'), false)

  clock.__testHooks.reset()
})

test('clock: ensureJob auto-starts once, resetAll clears every job and the v2 index', async () => {
  const clock = await clockModule()
  clock.__testHooks.reset()

  let now = 5000
  clock.__testHooks.setNow(() => now)

  clock.ensureJob('report')
  const firstElapsed = clock.jobElapsed('report')
  now += 1000
  clock.ensureJob('report') // must not restart the job
  assert.equal(clock.jobElapsed('report'), firstElapsed + 1)

  assert.equal(clock.getV2Index(), 0)
  clock.advanceV2Index(3)
  clock.advanceV2Index(3)
  assert.equal(clock.getV2Index(), 2)
  clock.advanceV2Index(3) // clamps at max - 1
  assert.equal(clock.getV2Index(), 2)

  clock.resetAll()
  assert.equal(clock.jobStarted('report'), false)
  assert.equal(clock.getV2Index(), 0)

  clock.__testHooks.reset()
})
