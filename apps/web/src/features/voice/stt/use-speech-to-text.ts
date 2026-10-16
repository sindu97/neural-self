/**
 * Voice input with the browser's Web Speech API, tuned for low latency:
 *
 * - interim results, so words appear while the user is still speaking;
 * - a short silence cut-off that ends the turn as soon as the user pauses;
 * - on-device recognition (`processLocally`, Chrome 138+) whenever the
 *   language pack is installed, which skips the round trip to a cloud
 *   service. Otherwise the browser's default (network) recogniser is used.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

interface RecognitionResult {
  readonly isFinal: boolean
  readonly [index: number]: { transcript: string } | undefined
}
interface Recognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  processLocally?: boolean
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: { resultIndex: number; results: ArrayLike<RecognitionResult> }) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
}
interface RecognitionConstructor {
  new (): Recognition
  available?: (options: { langs: string[]; processLocally: boolean }) => Promise<string>
}

function getRecognition(): RecognitionConstructor | null {
  if (typeof window === 'undefined') return null
  const scope = window as unknown as Record<string, RecognitionConstructor | undefined>
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null
}

const ERROR_MESSAGES: Record<string, string> = {
  'not-allowed': 'Microphone access is blocked. Allow the microphone in your browser and try again.',
  'service-not-allowed': 'Microphone access is blocked. Allow the microphone in your browser and try again.',
  'audio-capture': 'No microphone was found. Check that one is connected.',
  network: 'Voice input needs an internet connection in this browser.',
  'no-speech': "I didn't hear anything. Try again.",
}

/** State and controls returned by {@link useSpeechToText}. */
export interface SpeechToText {
  isSupported: boolean
  isListening: boolean
  /** Final + in-progress words, for display while listening. */
  text: string
  error: string | null
  isOnDevice: boolean
  /** Start listening. The turn ends via `onFinish` (after a pause, or `finish()`). */
  start: () => void
  /** Stop now and finish the turn with what was heard. */
  finish: () => void
  /** Stop and discard. */
  cancel: () => void
}

/**
 * Voice input via the browser's Web Speech API; calls `onFinish` once per spoken turn.
 *
 * @remarks
 * Turns end `silenceMs` after the user stops talking, or on `finish()`. Recognition runs
 * on-device when the browser supports it for `lang`.
 */
export function useSpeechToText({
  onFinish,
  lang = 'en-US',
  silenceMs = 1000,
}: {
  /** Called once per turn with the full transcript (may be empty). */
  onFinish: (transcript: string) => void
  lang?: string
  silenceMs?: number
}): SpeechToText {
  const Recognition = getRecognition()
  const [isListening, setIsListening] = useState(false)
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isOnDevice, setIsOnDevice] = useState(false)

  const recognition = useRef<Recognition | null>(null)
  const finalText = useRef('')
  const interimText = useRef('')
  const silenceTimer = useRef<number | null>(null)
  const discard = useRef(false)
  const onFinishRef = useRef(onFinish)
  useEffect(() => {
    onFinishRef.current = onFinish
  }, [onFinish])

  // Is on-device recognition ready for this language? Checked in the
  // background on the first use (never at page load: some Chromium builds
  // without the on-device service crash on this call), so starting the mic
  // never waits for it. Later turns then run on-device.
  const probed = useRef(false)
  const probeOnDevice = useCallback(() => {
    if (probed.current || !Recognition?.available) return
    probed.current = true
    Recognition.available({ langs: [lang], processLocally: true })
      .then((state) => setIsOnDevice(state === 'available'))
      .catch(() => undefined)
  }, [Recognition, lang])

  const clearTimer = () => {
    if (silenceTimer.current !== null) window.clearTimeout(silenceTimer.current)
    silenceTimer.current = null
  }

  const finish = useCallback(() => {
    clearTimer()
    recognition.current?.stop() // onend delivers the transcript
  }, [])

  const cancel = useCallback(() => {
    discard.current = true
    clearTimer()
    recognition.current?.abort()
  }, [])

  const start = useCallback(() => {
    if (!Recognition || recognition.current) return
    probeOnDevice()
    setError(null)
    setText('')
    finalText.current = ''
    interimText.current = ''
    discard.current = false

    const instance = new Recognition()
    instance.lang = lang
    instance.continuous = true
    instance.interimResults = true
    if (isOnDevice) instance.processLocally = true

    instance.onresult = (event) => {
      let interim = ''
      for (let index = event.resultIndex; index < event.results.length; index++) {
        const result = event.results[index]
        const words = result?.[0]?.transcript ?? ''
        if (result?.isFinal) finalText.current = `${finalText.current} ${words}`
        else interim += words
      }
      interimText.current = interim
      setText(`${finalText.current} ${interim}`.replace(/\s+/g, ' ').trim())
      // Restart the pause clock on every result: the turn ends `silenceMs`
      // after the user stops talking, not after they started.
      clearTimer()
      silenceTimer.current = window.setTimeout(() => instance.stop(), silenceMs)
    }
    instance.onerror = (event) => {
      if (event.error === 'aborted') return
      setError(ERROR_MESSAGES[event.error] ?? `Voice input error: ${event.error}`)
    }
    instance.onend = () => {
      clearTimer()
      recognition.current = null
      setIsListening(false)
      // On stop, the last interim words may not have been finalised yet: keep them.
      const transcript = `${finalText.current} ${interimText.current}`.replace(/\s+/g, ' ').trim()
      setText('')
      if (!discard.current) onFinishRef.current(transcript)
    }

    recognition.current = instance
    try {
      instance.start()
      setIsListening(true)
    } catch {
      recognition.current = null
      setError('Voice input could not start. Is the microphone in use by another app?')
    }
  }, [Recognition, isOnDevice, lang, silenceMs, probeOnDevice])

  // Release the microphone when the component unmounts.
  useEffect(
    () => () => {
      discard.current = true
      recognition.current?.abort()
    },
    [],
  )

  return { isSupported: Boolean(Recognition), isListening, text, error, isOnDevice, start, finish, cancel }
}
