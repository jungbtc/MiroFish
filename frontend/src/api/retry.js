const RETRYABLE_METHODS = new Set(['get', 'head', 'options'])
const RETRYABLE_STATUSES = new Set([408, 425, 429, 500, 502, 503, 504])

export function shouldRetryRequest(error) {
  const method = String(error?.method || error?.config?.method || '').toLowerCase()
  if (!RETRYABLE_METHODS.has(method)) return false

  const status = error?.status ?? error?.response?.status
  return status == null || RETRYABLE_STATUSES.has(Number(status))
}

export async function requestWithRetry(requestFn, maxRetries = 3, delay = 1000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn()
    } catch (error) {
      if (i === maxRetries - 1 || !shouldRetryRequest(error)) {
        throw error
      }

      console.warn(`Request failed, retrying (${i + 1}/${maxRetries})...`)
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
    }
  }
}
