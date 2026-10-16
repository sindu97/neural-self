import { formatBytes, formatRelativeTime, greeting, initials } from './format'

describe('format helpers', () => {
  it('formats sizes', () => {
    expect(formatBytes(null)).toBe('—')
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2 KB')
    expect(formatBytes(2.4 * 1024 * 1024)).toBe('2.4 MB')
  })

  it('formats relative times', () => {
    const now = new Date('2026-10-15T12:00:00Z')
    expect(formatRelativeTime('2026-10-15T11:59:30Z', now)).toBe('just now')
    expect(formatRelativeTime('2026-10-15T10:00:00Z', now)).toMatch(/2 hours ago/)
  })

  it('builds greetings and initials', () => {
    expect(greeting(new Date('2026-10-15T08:00:00'))).toBe('Good morning')
    expect(greeting(new Date('2026-10-15T20:00:00'))).toBe('Good evening')
    expect(initials('Surinder  Rana')).toBe('SR')
  })
})
