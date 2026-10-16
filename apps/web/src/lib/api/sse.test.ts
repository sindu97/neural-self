import { parseEvents } from './sse'

describe('parseEvents', () => {
  it('parses complete events and keeps the incomplete tail', () => {
    const { events, rest } = parseEvents(
      'event: start\ndata: {"citations": []}\n\nevent: token\ndata: {"delta": "Hel"}\n\nevent: tok',
    )
    expect(events).toEqual([
      { event: 'start', data: { citations: [] } },
      { event: 'token', data: { delta: 'Hel' } },
    ])
    expect(rest).toBe('event: tok')
  })

  it('handles events split across network chunks', () => {
    let buffer = 'event: token\ndata: {"del'
    let parsed = parseEvents(buffer)
    expect(parsed.events).toEqual([])

    buffer = parsed.rest + 'ta": "lo"}\n\n'
    parsed = parseEvents(buffer)
    expect(parsed.events).toEqual([{ event: 'token', data: { delta: 'lo' } }])
    expect(parsed.rest).toBe('')
  })

  it('defaults the event name and keeps non-JSON data as text', () => {
    expect(parseEvents('data: plain text\n\n').events).toEqual([{ event: 'message', data: 'plain text' }])
  })
})
