import { http as mswHttp, HttpResponse } from 'msw'

import { API, envelope, errorEnvelope, sessionTokens } from '../../../tests/msw/handlers'
import { server } from '../../../tests/msw/server'
import { getOne } from './client'
import { onSessionExpired, setAccessToken } from './session'

const unauthorized = () =>
  HttpResponse.json(errorEnvelope('UNAUTHORIZED', 'Authentication required.'), { status: 401 })

describe('http client', () => {
  it('attaches the access token', async () => {
    let auth: string | null = null
    server.use(
      mswHttp.get(`${API}/auth/me`, ({ request }) => {
        auth = request.headers.get('Authorization')
        return HttpResponse.json(envelope([{ ok: true }]))
      }),
    )
    setAccessToken('abc')

    await getOne('/auth/me')

    expect(auth).toBe('Bearer abc')
  })

  it('refreshes once on 401 and replays the request with the new token', async () => {
    const seen: (string | null)[] = []
    server.use(
      mswHttp.get(`${API}/documents/1`, ({ request }) => {
        const auth = request.headers.get('Authorization')
        seen.push(auth)
        return auth === 'Bearer renewed' ? HttpResponse.json(envelope([{ id: '1' }])) : unauthorized()
      }),
      mswHttp.post(`${API}/auth/refresh`, () => HttpResponse.json(envelope([sessionTokens('renewed')]))),
    )
    setAccessToken('expired')

    await expect(getOne('/documents/1')).resolves.toEqual({ id: '1' })
    expect(seen).toEqual(['Bearer expired', 'Bearer renewed'])
  })

  it('signs the user out when the refresh also fails', async () => {
    server.use(mswHttp.get(`${API}/documents/1`, unauthorized))
    const expired = vi.fn()
    const unsubscribe = onSessionExpired(expired)
    setAccessToken('expired')

    await expect(getOne('/documents/1')).rejects.toMatchObject({ code: 'UNAUTHORIZED' })
    expect(expired).toHaveBeenCalledOnce()
    unsubscribe()
  })

  it('unwraps errors into ApiError with the server message', async () => {
    server.use(
      mswHttp.get(`${API}/documents/x`, () =>
        HttpResponse.json(errorEnvelope('DOCUMENT_NOT_FOUND', 'Document not found.'), {
          status: 404,
          headers: { 'X-Request-ID': 'r-9' },
        }),
      ),
    )

    await expect(getOne('/documents/x')).rejects.toMatchObject({
      status: 404,
      code: 'DOCUMENT_NOT_FOUND',
      message: 'Document not found.',
      requestId: 'r-9',
    })
  })
})
