import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { TooltipProvider } from '@/components/ui/tooltip'

import { Composer } from './Composer'

// A controllable stand-in for the browser's SpeechRecognition.
class FakeRecognition {
  static current: FakeRecognition | null = null
  lang = ''
  continuous = false
  interimResults = false
  processLocally?: boolean
  onresult: ((event: unknown) => void) | null = null
  onerror: ((event: { error: string }) => void) | null = null
  onend: (() => void) | null = null
  constructor() {
    FakeRecognition.current = this
  }
  start() {}
  stop() {
    this.onend?.()
  }
  abort() {
    this.onend?.()
  }
  say(text: string, isFinal: boolean) {
    const result = Object.assign([{ transcript: text }], { isFinal })
    this.onresult?.({ resultIndex: 0, results: [result] })
  }
}

function renderComposer(onSend = vi.fn()) {
  render(
    <TooltipProvider>
      <Composer onSend={onSend} onStop={vi.fn()} streaming={false} />
    </TooltipProvider>,
  )
  return onSend
}

describe('Composer voice input', () => {
  beforeEach(() => vi.stubGlobal('webkitSpeechRecognition', FakeRecognition))
  afterEach(() => vi.unstubAllGlobals())

  it('shows words while listening and sends the spoken question after a pause', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const onSend = renderComposer()

    await userEvent.click(screen.getByRole('button', { name: 'Ask by voice' }))
    act(() => FakeRecognition.current!.say('where does photosynthesis', false))
    expect(screen.getByLabelText('Your question')).toHaveValue('where does photosynthesis')

    act(() => FakeRecognition.current!.say('where does photosynthesis take place', true))
    act(() => vi.advanceTimersByTime(1100)) // the pause ends the turn

    expect(onSend).toHaveBeenCalledWith('where does photosynthesis take place', { byVoice: true })
    vi.useRealTimers()
  })

  it('tapping the mic again sends immediately; Escape cancels', async () => {
    const onSend = renderComposer()

    await userEvent.click(screen.getByRole('button', { name: 'Ask by voice' }))
    act(() => FakeRecognition.current!.say('first question', true))
    await userEvent.click(screen.getByRole('button', { name: 'Stop and send' }))
    expect(onSend).toHaveBeenLastCalledWith('first question', { byVoice: true })

    await userEvent.click(screen.getByRole('button', { name: 'Ask by voice' }))
    act(() => FakeRecognition.current!.say('never mind', false))
    await userEvent.keyboard('{Escape}')
    expect(onSend).toHaveBeenCalledTimes(1)
  })

  it('typed questions are marked as not spoken', async () => {
    const onSend = renderComposer()
    await userEvent.type(screen.getByLabelText('Your question'), 'typed question{Enter}')
    expect(onSend).toHaveBeenCalledWith('typed question', { byVoice: false })
  })

  it('explains when the browser has no voice input', () => {
    vi.stubGlobal('webkitSpeechRecognition', undefined)
    renderComposer()
    expect(screen.getByRole('button', { name: 'Voice input unavailable' })).toBeDisabled()
  })
})
