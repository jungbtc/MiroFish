// Fake axios adapter for demo mode. Given a list of routes, returns an
// async function with the same signature as a real axios adapter
// (config => Promise<response>), so it can be dropped straight into
// `service.defaults.adapter`.
//
// Route entry contract (implemented by src/demo/handlers/*.js, aggregated
// by src/demo/routes.js):
//   {
//     method: 'get' | 'post' | 'delete',
//     pattern: /^\/api\/graph\/task\/(?<taskId>[^/?]+)$/,
//     latency: 'ai' | 'read' | number | [min, max],
//     handler({ params, query, body, config }) // sync or async
//   }
// `handler` returns the value placed under `data` in the
// `{ success: true, data }` envelope. If `config.responseType` is 'blob' or
// 'text' the return value is used as-is (no envelope). A handler may also
// return `{ __status: 201, data: ... }` to override the response status
// while still going through the normal envelope.

import { AI_LATENCY_MS, READ_LATENCY_MS } from './timings.js'

const STATUS_TEXT = { 200: 'OK', 201: 'Created', 204: 'No Content' }

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

const jitter = ([min, max]) => min + Math.random() * (max - min)

const resolveLatencyMs = latency => {
  if (latency === 'ai') return jitter(AI_LATENCY_MS)
  if (Array.isArray(latency)) return jitter(latency)
  if (typeof latency === 'number') return latency
  return jitter(READ_LATENCY_MS) // 'read', undefined, or anything unrecognized
}

const parseBody = data => {
  if (typeof data !== 'string') return data
  try {
    return JSON.parse(data)
  } catch {
    return data
  }
}

const isStatusOverride = result =>
  Boolean(result) && typeof result === 'object' && !Array.isArray(result) && '__status' in result

const buildResponse = (config, data, status) => ({
  data,
  status,
  statusText: STATUS_TEXT[status] || 'OK',
  headers: {},
  config,
  request: { demo: true }
})

export const createDemoAdapter = routes => async config => {
  const method = (config.method || 'get').toLowerCase()
  const url = (config.url || '').split('?')[0]

  const route = routes.find(r => r.method === method && r.pattern.test(url))

  if (!route) {
    console.warn('[demo] unmatched', method, url)
    await sleep(120)
    return buildResponse(config, { success: true, data: {} }, 200)
  }

  await sleep(resolveLatencyMs(route.latency))

  const match = route.pattern.exec(url)
  const params = match?.groups || {}
  const query = config.params || {}
  const body = parseBody(config.data)

  const result = await route.handler({ params, query, body, config })

  const isRawResponse = config.responseType === 'blob' || config.responseType === 'text'
  if (isRawResponse) {
    return buildResponse(config, result, 200)
  }

  if (isStatusOverride(result)) {
    return buildResponse(config, { success: true, data: result.data }, result.__status)
  }

  return buildResponse(config, { success: true, data: result }, 200)
}
