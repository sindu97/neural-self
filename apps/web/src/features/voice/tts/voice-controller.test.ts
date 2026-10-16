import type { FromWorker, ToWorker } from './messages'

// Fake audio output: records what plays, finishes on demand.
const player = vi.hoisted(() => ({
  played: [] as Float32Array[],
  idle: null as (() => void) | null,
  playing: false,
  stopped: 0,
}))
vi.mock('./audio-player', () => ({
  AudioPlayer: class {
    unlock() {}
    setIdleListener(listener: () => void) {
      player.idle = listener
    }
    get playing() {
      return player.playing
    }
    play(samples: Float32Array) {
      player.played.push(samples)
      player.playing = true
    }
    stop() {
      player.stopped += 1
      player.playing = false
    }
  },
}))

// Fake worker: records requests; tests answer them.
class FakeWorker {
  static last: FakeWorker
  sent: ToWorker[] = []
  onmessage: ((event: MessageEvent<FromWorker>) => void) | null = null
  constructor() {
    FakeWorker.last = this
  }
  postMessage(message: ToWorker) {
    this.sent.push(message)
  }
  terminate() {}
  reply(message: FromWorker) {
    this.onmessage?.({ data: message } as MessageEvent<FromWorker>)
  }
  get requests() {
    return this.sent.filter((m): m is Extract<ToWorker, { type: 'synthesize' }> => m.type === 'synthesize')
  }
}
vi.stubGlobal('Worker', FakeWorker)

const { VoiceController } = await import('./voice-controller')

function audioFor(request: { id: number; generation: number }): FromWorker {
  return {
    type: 'audio',
    id: request.id,
    generation: request.generation,
    samples: new Float32Array(4),
    sampleRate: 22050,
  }
}

describe('VoiceController', () => {
  beforeEach(() => {
    player.played = []
    player.playing = false
    player.stopped = 0
  })

  it('speaks a streaming answer sentence by sentence, starting before it is complete', () => {
    const voice = new VoiceController()
    voice.startAnswer('a1')
    const worker = FakeWorker.last
    expect(worker.sent[0]).toMatchObject({ type: 'init' })

    voice.append('a1', 'Photosynthesis happens in the chloroplasts. It ')
    expect(worker.requests.map((r) => r.text)).toEqual(['Photosynthesis happens in the chloroplasts.'])

    voice.append('a1', 'needs sunlight [1]. More')
    voice.finish('a1')
    expect(worker.requests.map((r) => r.text)).toEqual([
      'Photosynthesis happens in the chloroplasts.',
      'It needs sunlight .',
      'More',
    ])
    expect(voice.getSnapshot().speakingKey).toBe('a1')
  })

  it('opens with a short phrase when the first sentence is long', () => {
    const voice = new VoiceController()
    voice.startAnswer('a1')
    voice.append('a1', 'Chloroplasts, the green organelles in plant cells, are where it happens and')
    // Cut at the first clause boundary at least 14 characters in.
    expect(FakeWorker.last.requests.map((r) => r.text)).toEqual([
      'Chloroplasts, the green organelles in plant cells,',
    ])
  })

  it('plays results and becomes idle once everything has been heard', () => {
    const voice = new VoiceController()
    voice.speak('a1', 'One full sentence here. And another one.')
    const worker = FakeWorker.last
    for (const request of worker.requests) worker.reply(audioFor(request))
    expect(player.played).toHaveLength(2)
    expect(voice.getSnapshot().speakingKey).toBe('a1')

    player.playing = false
    player.idle?.()
    expect(voice.getSnapshot().speakingKey).toBeNull()
  })

  it('mute silences immediately and ignores audio still being synthesized', () => {
    const voice = new VoiceController()
    voice.speak('a1', 'One full sentence here. And another one.')
    const worker = FakeWorker.last
    const [first, second] = worker.requests

    voice.stop()
    expect(player.stopped).toBeGreaterThan(0)
    expect(worker.sent.at(-1)).toMatchObject({ type: 'cancel' })
    expect(voice.getSnapshot().speakingKey).toBeNull()

    worker.reply(audioFor(first!))
    worker.reply(audioFor(second!))
    expect(player.played).toHaveLength(0)
  })

  it('moves the speaking state to the saved message id', () => {
    const voice = new VoiceController()
    voice.startAnswer('streaming')
    voice.rekey('streaming', 'message-42')
    expect(voice.getSnapshot().speakingKey).toBe('message-42')
  })

  it('reports a voice that failed to load', () => {
    const voice = new VoiceController()
    voice.prepare()
    FakeWorker.last.reply({ type: 'error', message: 'Voice file not found', fatal: true })
    expect(voice.getSnapshot()).toMatchObject({ modelStatus: 'error', error: 'Voice file not found' })
  })
})
