import { http, HttpResponse } from 'msw'

import { API, envelope, errorEnvelope, sessionTokens } from '../../../tests/msw/handlers'
import { server } from '../../../tests/msw/server'
import { ApiError } from './errors'
import { getAccessToken, refreshSession } from './session'

describe('refreshSession', () => {
  it('sends the CSRF header and stores the new access token in memory only', async () => {
    let csrf: string | null = null
    server.use(
      http.post(`${API}/auth/refresh`, ({ request }) => {
        csrf = request.headers.get('X-NeuralShelf-CSRF')
        return HttpResponse.json(envelope([sessionTokens('fresh')]))
      }),
    )

    const tokens = await refreshSession()

    expect(csrf).toBe('1')
    expect(tokens.user.email).toBe('asha@example.com')
    expect(getAccessToken()).toBe('fresh')
    expect(JSON.stringify({ ...localStorage, ...sessionStorage })).not.toContain('fresh')
  })

  it('makes one request for concurrent callers, because refresh tokens are single-use', async () => {
    let calls = 0
    server.use(
      http.post(`${API}/auth/refresh`, async () => {
        calls += 1
        await new Promise((resolve) => setTimeout(resolve, 20))
        return HttpResponse.json(envelope([sessionTokens()]))
      }),
    )

    await Promise.all([refreshSession(), refreshSession(), refreshSession()])

    expect(calls).toBe(1)
  })

  it('rejects with an ApiError when the cookie is missing or revoked', async () => {
    server.use(
      http.post(`${API}/auth/refresh`, () =>
        HttpResponse.json(errorEnvelope('INVALID_REFRESH_TOKEN', 'Expired.'), { status: 401 }),
      ),
    )

    await expect(refreshSession()).rejects.toBeInstanceOf(ApiError)
    expect(getAccessToken()).toBeNull()
  })
})
