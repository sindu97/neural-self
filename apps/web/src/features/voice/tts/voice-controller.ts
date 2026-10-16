/**
 * Spoken answers: one controller for the whole app.
 *
 * Answer text is fed in as it streams (start -> append... -> finish). It is
 * cut into sentences, synthesized in order by the Piper worker and played
 * back-to-back, so speech starts while the answer is still being written.
 * Each spoken answer has a key (a message id), which lets the UI show a mute
 * button on exactly the answer that is speaking.
 */
import { cleanForSpeech, drainSentences, takeFirstFragment } from '../utils/sentences'
import { AudioPlayer } from './audio-player'
import type { FromWorker, ToWorker } from './messages'

export type ModelStatus = 'idle' | 'loading' | 'ready' | 'error'

/** Voice state for the UI. */
export interface VoiceState {
  modelStatus: ModelStatus
  /** Model download progress, 0–1, while loading. */
  progress: number | null
  error: string | null
  /** Key of the answer being spoken, if any. */
  speakingKey: string | null
  /** Read every answer aloud, not only answers to spoken questions. */
  autoRead: boolean
}

/** Latency logging in development, e.g. "[voice] first audio 412 ms after the first words". */
const debug = (...args: unknown[]) => {
  if (import.meta.env.DEV) console.info('[voice]', ...args)
}

const VOICE_MODEL_URL = '/models/indian-accent-60.onnx'
const VOICE_CONFIG_URL = '/models/indian-accent-60.json'
const AUTO_READ_KEY = 'neuralshelf.voice.autoRead'

function loadAutoRead(): boolean {
  try {
    return localStorage.getItem(AUTO_READ_KEY) === 'true'
  } catch {
    return false
  }
}

/** Spoken answers for the whole app; see the module comment. Use the shared {@link voice} instance. */
export class VoiceController {
  private state: VoiceState = {
    modelStatus: 'idle',
    progress: null,
    error: null,
    speakingKey: null,
    autoRead: loadAutoRead(),
  }
  private listeners = new Set<() => void>()
  private worker: Worker | null = null
  private player = new AudioPlayer()

  // The answer being spoken.
  private generation = 0
  private nextRequestId = 1
  private buffer = ''
  private queuedAny = false
  private finished = false
  private pending = 0
  private loadStartedAt = 0
  private firstTextAt: number | null = null
  private firstAudioLogged = false

  constructor() {
    this.player.setIdleListener(() => this.settleIfDone())
  }

  // ---- React integration (useSyncExternalStore) --------------------------

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  getSnapshot = () => this.state

  private update(changes: Partial<VoiceState>) {
    this.state = { ...this.state, ...changes }
    this.listeners.forEach((listener) => listener())
  }

  // ---- setup ---------------------------------------------------------------

  /** Start loading the voice in the background (first time: ~60 MB, then cached). */
  prepare(): void {
    if (this.worker && this.state.modelStatus !== 'error') return
    if (typeof Worker === 'undefined') {
      this.update({ modelStatus: 'error', error: 'Spoken answers are not supported in this browser.' })
      return
    }
    this.worker?.terminate()
    this.worker = new Worker(new URL('./piper.worker.ts', import.meta.url), { type: 'module' })
    this.worker.onmessage = (event: MessageEvent<FromWorker>) => this.onWorkerMessage(event.data)
    this.loadStartedAt = performance.now()
    this.update({ modelStatus: 'loading', progress: 0, error: null })
    this.send({ type: 'init', modelUrl: VOICE_MODEL_URL, configUrl: VOICE_CONFIG_URL })
  }

  /** Must run inside a user gesture (click/key) before audio can play. */
  unlock(): void {
    this.player.unlock()
  }

  setAutoRead(enabled: boolean): void {
    try {
      localStorage.setItem(AUTO_READ_KEY, String(enabled))
    } catch {
      // storage unavailable: the setting just won't persist
    }
    this.update({ autoRead: enabled })
    if (!enabled) this.stop()
  }

  // ---- speaking ------------------------------------------------------------

  /** Begin speaking a new answer, stopping whatever was playing. */
  startAnswer(key: string): void {
    this.stop()
    this.prepare()
    this.buffer = ''
    this.queuedAny = false
    this.finished = false
    this.pending = 0
    this.firstTextAt = null
    this.firstAudioLogged = false
    this.update({ speakingKey: key })
  }

  /** Add streamed text to the answer being spoken. */
  append(key: string, text: string): void {
    if (key !== this.state.speakingKey) return
    this.firstTextAt ??= performance.now()
    this.buffer += text
    const { sentences, rest } = drainSentences(this.buffer)
    this.buffer = rest
    sentences.forEach((sentence) => this.enqueue(sentence))

    // Start on a short opening phrase instead of waiting for a whole sentence.
    if (!this.queuedAny) {
      const fragment = takeFirstFragment(this.buffer)
      if (fragment) {
        this.buffer = fragment.rest
        this.enqueue(fragment.fragment)
      }
    }
  }

  /** The answer is complete: speak whatever is left. */
  finish(key: string): void {
    if (key !== this.state.speakingKey) return
    if (this.buffer.trim()) this.enqueue(this.buffer)
    this.buffer = ''
    this.finished = true
    this.settleIfDone()
  }

  /** Read a finished answer aloud. */
  speak(key: string, text: string): void {
    this.startAnswer(key)
    this.append(key, `${text} `)
    this.finish(key)
  }

  /** The streaming answer got its real id once saved. */
  rekey(from: string, to: string): void {
    if (this.state.speakingKey === from) this.update({ speakingKey: to })
  }

  /** Mute: silence immediately and drop everything still queued. */
  stop(): void {
    this.generation += 1
    this.send({ type: 'cancel', generation: this.generation })
    this.player.stop()
    this.buffer = ''
    this.pending = 0
    this.finished = true
    if (this.state.speakingKey !== null) this.update({ speakingKey: null })
  }

  // ---- internals -------------------------------------------------------------

  private enqueue(text: string) {
    const speakable = cleanForSpeech(text).trim()
    if (!/[\p{L}\p{N}]/u.test(speakable)) return // nothing pronounceable
    this.queuedAny = true
    this.pending += 1
    this.send({ type: 'synthesize', id: this.nextRequestId++, generation: this.generation, text: speakable })
  }

  private settleIfDone() {
    if (this.finished && this.pending === 0 && !this.player.playing && this.state.speakingKey !== null) {
      this.update({ speakingKey: null })
    }
  }

  private send(message: ToWorker) {
    this.worker?.postMessage(message)
  }

  private onWorkerMessage(message: FromWorker) {
    switch (message.type) {
      case 'progress':
        this.update({ progress: message.total ? message.loaded / message.total : null })
        break
      case 'ready':
        debug(
          `ready in ${Math.round(performance.now() - this.loadStartedAt)} ms, ${message.threads} thread(s)`,
        )
        this.update({ modelStatus: 'ready', progress: null })
        break
      case 'audio':
        if (message.generation !== this.generation) return
        this.pending -= 1
        if (!this.firstAudioLogged && this.firstTextAt !== null) {
          this.firstAudioLogged = true
          debug(`first audio ${Math.round(performance.now() - this.firstTextAt)} ms after the first words`)
        }
        this.player.play(message.samples, message.sampleRate)
        break
      case 'skipped':
        if (message.generation !== this.generation) return
        this.pending -= 1
        this.settleIfDone()
        break
      case 'error':
        if (message.fatal) {
          this.update({ modelStatus: 'error', progress: null, error: message.message })
          this.stop()
        } else if (message.generation === this.generation) {
          this.pending -= 1
          this.settleIfDone()
        }
        break
    }
  }
}

/** The app-wide instance: one voice, one worker, one audio output. */
export const voice = new VoiceController()
