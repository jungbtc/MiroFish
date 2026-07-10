import assert from 'node:assert/strict'
import test from 'node:test'

import { requestWithRetry } from '../src/api/retry.js'

function requestError({ method, status, code, useAxiosConfig = false }) {
  const error = new Error('request failed')
  if (useAxiosConfig) {
    error.config = { method }
  } else {
    error.method = method
  }
  if (status != null) error.status = status
  if (code) error.code = code
  return error
}

test('does not retry POST requests on retryable server errors', async () => {
  let attempts = 0

  await assert.rejects(
    () => requestWithRetry(async () => {
      attempts += 1
      throw requestError({ method: 'post', status: 503 })
    }, 3, 0),
    /request failed/
  )

  assert.equal(attempts, 1)
})

test('does not retry POST requests when the network result is ambiguous', async () => {
  let attempts = 0

  await assert.rejects(
    () => requestWithRetry(async () => {
      attempts += 1
      throw requestError({
        method: 'post',
        code: 'ECONNABORTED',
        useAxiosConfig: true
      })
    }, 3, 0),
    /request failed/
  )

  assert.equal(attempts, 1)
})

test('retries safe GET requests on transient server errors', async () => {
  let attempts = 0

  const result = await requestWithRetry(async () => {
    attempts += 1
    if (attempts < 3) {
      throw requestError({ method: 'get', status: 503 })
    }
    return 'ok'
  }, 3, 0)

  assert.equal(result, 'ok')
  assert.equal(attempts, 3)
})

test('does not retry safe methods on non-retryable client errors', async () => {
  let attempts = 0

  await assert.rejects(
    () => requestWithRetry(async () => {
      attempts += 1
      throw requestError({ method: 'get', status: 400 })
    }, 3, 0),
    /request failed/
  )

  assert.equal(attempts, 1)
})
