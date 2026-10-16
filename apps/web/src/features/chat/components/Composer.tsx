import { ArrowUp, Square } from 'lucide-react'
import { type KeyboardEvent, useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { LIMITS } from '@/core/constants'
import { MicButton, useSpeechToText, voice } from '@/features/voice'

/** How a question was asked. */
export interface SendOptions {
  /** The question was spoken: its answer is read aloud. */
  byVoice: boolean
}

/**
 * Question box: type and press Enter, or tap the mic and speak (sends after a pause).
 *
 * @remarks
 * Shows a stop button while an answer is streaming.
 */
export function Composer({
  onSend,
  onStop,
  streaming,
  disabled,
  autoFocus,
}: {
  onSend: (question: string, options: SendOptions) => void
  onStop: () => void
  streaming: boolean
  disabled?: boolean
  autoFocus?: boolean
}) {
  const [value, setValue] = useState('')
  const textarea = useRef<HTMLTextAreaElement>(null)

  // A spoken question is sent as soon as the user pauses.
  const stt = useSpeechToText({
    onFinish: (transcript) => {
      if (transcript && !streaming && !disabled) onSend(transcript, { byVoice: true })
      else if (transcript) setValue(transcript) // can't send right now: keep it to send later
    },
  })
  const shown = stt.isListening ? stt.text : value

  // Grow with the text, up to a limit.
  useEffect(() => {
    const element = textarea.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, 200)}px`
  }, [shown])

  const submit = () => {
    const question = value.trim()
    if (!question || streaming || disabled) return
    voice.unlock() // inside the click/keypress, so the answer may be read aloud
    onSend(question, { byVoice: false })
    setValue('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (stt.isListening && event.key === 'Escape') {
      event.preventDefault()
      stt.cancel()
      return
    }
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div>
      <div className="rounded-2xl border bg-card p-2 shadow-soft focus-within:border-ring/60">
        <div className="flex items-end gap-1.5">
          <textarea
            ref={textarea}
            value={shown}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={onKeyDown}
            readOnly={stt.isListening}
            rows={1}
            maxLength={LIMITS.maxQuestionLength}
            autoFocus={autoFocus}
            disabled={disabled}
            placeholder={
              stt.isListening
                ? 'Listening… pause to send, Esc to cancel'
                : 'Ask a question about your documents…'
            }
            aria-label="Your question"
            className="max-h-[200px] min-h-10 flex-1 resize-none bg-transparent px-2.5 py-2.5 text-[13px] outline-none placeholder:text-subtle disabled:opacity-50"
          />
          <div className="flex items-center gap-1 pb-0.5">
            <MicButton stt={stt} disabled={disabled || streaming} />
            {streaming ? (
              <Button size="icon" variant="outline" onClick={onStop} aria-label="Stop generating">
                <Square className="fill-current" />
              </Button>
            ) : (
              <Button
                size="icon"
                onClick={submit}
                disabled={!value.trim() || disabled || stt.isListening}
                aria-label="Send question"
              >
                <ArrowUp />
              </Button>
            )}
          </div>
        </div>
      </div>
      {stt.error && (
        <p className="mt-1.5 px-1 text-[11px] text-destructive" role="alert">
          {stt.error}
        </p>
      )}
    </div>
  )
}
