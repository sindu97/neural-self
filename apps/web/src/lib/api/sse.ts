/**
 * POST + Server-Sent Events, used for streaming chat answers.
 *
 * Built on fetch rather than Axios or EventSource: EventSource can't POST
 * or send an Authorization header, and Axios can't stream in browsers.
 */
import { env } from '@/core/config/env'

import { apiErrorFromResponse, toApiError } from './errors'
import { getAccessToken, notifySessionExpired, refreshSession } from './session'

/** One parsed event; `data` is decoded JSON when possible, otherwise text. */
export interface ServerSentEvent {
  event: string
  data: unknown
}

/** Parse complete events out of a text buffer; returns the unparsed remainder. */
export function parseEvents(buffer: string): { events: ServerSentEvent[]; rest: string } {
  const events: ServerSentEvent[] = []
  const blocks = buffer.split('\n\n')
  const rest = blocks.pop() ?? ''

  for (const block of blocks) {
    let event = 'message'
    const dataLines: string[] = []
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (dataLines.length === 0) continue
    const raw = dataLines.join('\n')
    let data: unknown = raw
    try {
      data = JSON.parse(raw)
    } catch {
      // keep raw text
    }
    events.push({ event, data })
  }
  return { events, rest }
}

/**
 * Stream events from a POST endpoint. Errors that happen before streaming
 * starts (404, 422, 503...) are thrown as ApiError, like any other request.
 */
export async function* streamEvents(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<ServerSentEvent> {
  const response = await openStream(path, body, signal)
  if (!response.body) return

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += value
      const { events, rest } = parseEvents(buffer)
      buffer = rest
      yield* events
    }
  } finally {
    reader.releaseLock()
  }
}

async function openStream(path: string, body: unknown, signal?: AbortSignal): Promise<Response> {
  const send = () =>
    fetch(`${env.apiBaseUrl}${path}`, {
      method: 'POST',
      credentials: 'include',
      signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
      },
      body: JSON.stringify(body),
    })

  let response: Response
  try {
    response = await send()
    if (response.status === 401) {
      try {
        await refreshSession()
      } catch {
        notifySessionExpired()
        throw await errorFrom(response)
      }
      response = await send()
    }
  } catch (error) {
    throw toApiError(error)
  }

  if (!response.ok) throw await errorFrom(response)
  return response
}

async function errorFrom(response: Response) {
  const body: unknown = await response.json().catch(() => null)
  return apiErrorFromResponse(response.status, body, response.headers)
}
