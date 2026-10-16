/**
 * Gapless playback of synthesized chunks through the Web Audio API.
 *
 * Each chunk is scheduled to start exactly when the previous one ends, and
 * stop() silences everything immediately, including a chunk mid-sentence.
 */
export class AudioPlayer {
  private context: AudioContext | null = null
  private sources = new Set<AudioBufferSourceNode>()
  private nextStart = 0
  private onIdle: (() => void) | null = null

  /** Browsers only allow audio after a user gesture: call this from a click. */
  unlock(): void {
    // Without Web Audio there is simply no spoken output, never a crash.
    if (typeof AudioContext === 'undefined') return
    this.context ??= new AudioContext()
    if (this.context.state === 'suspended') void this.context.resume()
  }

  /** Called whenever the last scheduled chunk finishes. */
  setIdleListener(listener: (() => void) | null): void {
    this.onIdle = listener
  }

  get playing(): boolean {
    return this.sources.size > 0
  }

  play(samples: Float32Array, sampleRate: number): void {
    this.unlock()
    const context = this.context
    if (!context) return
    const buffer = context.createBuffer(1, samples.length, sampleRate)
    buffer.copyToChannel(samples as Float32Array<ArrayBuffer>, 0)

    const source = context.createBufferSource()
    source.buffer = buffer
    source.connect(context.destination)

    // A small lead time avoids clicks when the queue has run dry.
    const startAt = Math.max(context.currentTime + 0.03, this.nextStart)
    this.nextStart = startAt + buffer.duration
    source.onended = () => {
      this.sources.delete(source)
      if (this.sources.size === 0) this.onIdle?.()
    }
    this.sources.add(source)
    source.start(startAt)
  }

  stop(): void {
    for (const source of this.sources) {
      source.onended = null
      try {
        source.stop()
      } catch {
        // already stopped
      }
    }
    this.sources.clear()
    this.nextStart = 0
  }
}
