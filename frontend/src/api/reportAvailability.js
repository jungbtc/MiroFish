const defaultSleep = ms => new Promise(resolve => setTimeout(resolve, ms))

export async function waitForReportAvailability(loadReport, options = {}) {
  const {
    maxAttempts = 20,
    delayMs = 500,
    shouldCancel = () => false,
    sleep = defaultSleep
  } = options

  if (!Number.isInteger(maxAttempts) || maxAttempts < 1) {
    throw new RangeError('maxAttempts must be a positive integer')
  }

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (shouldCancel()) return null

    try {
      return await loadReport()
    } catch (error) {
      const status = error?.status ?? error?.response?.status
      const canRetry = Number(status) === 404 && attempt < maxAttempts - 1
      if (!canRetry) throw error
      await sleep(delayMs)
    }
  }

  return null
}
