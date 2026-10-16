import { apiErrorFromResponse, describeError, toApiError } from './errors'

const headers = (values: Record<string, string>) => ({ get: (name: string) => values[name] ?? null })

describe('apiErrorFromResponse', () => {
  it('reads code, message, field errors, request id and Retry-After', () => {
    const error = apiErrorFromResponse(
      422,
      {
        code: 'VALIDATION_ERROR',
        message: 'Request validation failed.',
        data: [{ field: 'email', message: 'Bad' }],
      },
      headers({ 'x-request-id': 'req-1', 'retry-after': '30' }),
    )
    expect(error.status).toBe(422)
    expect(error.code).toBe('VALIDATION_ERROR')
    expect(error.fieldErrors).toEqual([{ field: 'email', message: 'Bad' }])
    expect(error.requestId).toBe('req-1')
    expect(error.retryAfterSeconds).toBe(30)
    expect(error.is('VALIDATION_ERROR', 'INVALID_FILE')).toBe(true)
  })

  it('falls back sensibly for non-envelope bodies', () => {
    const error = apiErrorFromResponse(502, '<html>Bad gateway</html>', headers({}))
    expect(error.code).toBe('INTERNAL_SERVER_ERROR')
    expect(error.message).toMatch(/something went wrong/i)
  })
})

describe('describeError', () => {
  it('adds the wait time to rate-limit messages', () => {
    const error = apiErrorFromResponse(
      429,
      { code: 'RATE_LIMITED', message: 'Too many requests.' },
      headers({ 'retry-after': '12' }),
    )
    expect(describeError(error)).toBe('Too many requests. Try again in 12s.')
  })

  it('treats fetch network failures as NETWORK_ERROR', () => {
    expect(toApiError(new TypeError('Failed to fetch')).code).toBe('NETWORK_ERROR')
  })
})
