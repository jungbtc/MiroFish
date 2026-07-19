import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { waitForReportAvailability } from '../src/api/reportAvailability.js'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

test('report generation status uses the authoritative POST contract', () => {
  const reportApi = readFileSync(resolve(frontendRoot, 'src/api/report.js'), 'utf8')

  assert.match(reportApi, /service\.post\('\/api\/report\/generate\/status', data\)/)
  assert.doesNotMatch(reportApi, /service\.get\(`\/api\/report\/generate\/status`/)
})

test('report availability retries transient 404 responses until success', async () => {
  let attempts = 0
  let sleeps = 0

  const result = await waitForReportAvailability(async () => {
    attempts += 1
    if (attempts < 3) {
      const error = new Error('not persisted yet')
      error.status = 404
      throw error
    }
    return { success: true }
  }, {
    maxAttempts: 5,
    delayMs: 0,
    sleep: async () => { sleeps += 1 }
  })

  assert.deepEqual(result, { success: true })
  assert.equal(attempts, 3)
  assert.equal(sleeps, 2)
})

test('report availability propagates non-404 failures immediately', async () => {
  let attempts = 0

  await assert.rejects(
    () => waitForReportAvailability(async () => {
      attempts += 1
      const error = new Error('server error')
      error.status = 500
      throw error
    }, { maxAttempts: 5, sleep: async () => {} }),
    /server error/
  )

  assert.equal(attempts, 1)
})

test('report availability bounds retries and supports route cancellation', async () => {
  let boundedAttempts = 0

  await assert.rejects(
    () => waitForReportAvailability(async () => {
      boundedAttempts += 1
      const error = new Error('still missing')
      error.status = 404
      throw error
    }, { maxAttempts: 3, delayMs: 0, sleep: async () => {} }),
    /still missing/
  )
  assert.equal(boundedAttempts, 3)

  let cancelled = false
  let cancelledAttempts = 0
  const cancelledResult = await waitForReportAvailability(async () => {
    cancelledAttempts += 1
    const error = new Error('not persisted yet')
    error.status = 404
    throw error
  }, {
    maxAttempts: 3,
    delayMs: 0,
    shouldCancel: () => cancelled,
    sleep: async () => { cancelled = true }
  })

  assert.equal(cancelledResult, null)
  assert.equal(cancelledAttempts, 1)
})
