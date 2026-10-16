/// <reference lib="webworker" />
/**
 * Piper text-to-speech in a Web Worker: text -> espeak-ng phonemes ->
 * phoneme IDs -> ONNX (onnxruntime-web, WASM) -> audio samples.
 *
 * Runs off the main thread so synthesis never blocks the UI. Requests are
 * handled one at a time, in order; a `cancel` drops everything older than the
 * given generation, including the result of a synthesis already running.
 */
import * as ort from 'onnxruntime-web/wasm'
import ortWasmMjsUrl from 'onnxruntime-web/ort-wasm-simd-threaded.mjs?url'
import ortWasmUrl from 'onnxruntime-web/ort-wasm-simd-threaded.wasm?url'
import { phonemize } from 'phonemizer'

import type { FromWorker, ToWorker } from './messages'
import { joinPhonemes, phonemesToIds, type PiperVoiceConfig, splitOnPunctuation } from './phonemes'

declare const self: DedicatedWorkerGlobalScope

const CACHE_NAME = 'neuralshelf-voice-v1'

ort.env.wasm.wasmPaths = { mjs: ortWasmMjsUrl, wasm: ortWasmUrl }
// Multi-threaded WASM needs a cross-origin-isolated page (COOP/COEP headers);
// otherwise ORT runs single-threaded, which still works, just slower.
ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1

let session: ort.InferenceSession | null = null
let config: PiperVoiceConfig | null = null
let ready: Promise<void> | null = null
let cancelledBefore = 0
let queue: Promise<void> = Promise.resolve()

const post = (message: FromWorker, transfer: Transferable[] = []) => self.postMessage(message, transfer)

/** Fetch with the Cache API, so the 60 MB model downloads once per browser. */
async function fetchCached(
  url: string,
  onProgress?: (loaded: number, total: number) => void,
): Promise<ArrayBuffer> {
  const cache = await caches.open(CACHE_NAME)
  const cached = await cache.match(url)
  if (cached) return cached.arrayBuffer()

  const response = await fetch(url)
  // A dev server answers a missing file with index.html; never cache that.
  if (!response.ok || (response.headers.get('content-type') ?? '').includes('text/html')) {
    throw new Error(`Voice file not found: ${url}. Run "npm run voice:setup".`)
  }

  const total = Number(response.headers.get('content-length')) || 0
  const reader = response.body?.getReader()
  if (!reader) return response.arrayBuffer()

  const chunks: Uint8Array[] = []
  let loaded = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
    loaded += value.length
    onProgress?.(loaded, total)
  }
  const body = new Uint8Array(loaded)
  let offset = 0
  for (const chunk of chunks) {
    body.set(chunk, offset)
    offset += chunk.length
  }
  await cache.put(url, new Response(body, { headers: { 'content-type': 'application/octet-stream' } }))
  return body.buffer
}

async function init(modelUrl: string, configUrl: string) {
  const configBuffer = await fetchCached(configUrl)
  config = JSON.parse(new TextDecoder().decode(configBuffer)) as PiperVoiceConfig
  const model = await fetchCached(modelUrl, (loaded, total) => post({ type: 'progress', loaded, total }))
  session = await ort.InferenceSession.create(model, { executionProviders: ['wasm'] })
  // Warm-up: the first run of a session (and the phonemizer) is much slower
  // than later ones. Pay that now, before anyone is waiting for an answer.
  await synthesize('Ready.')
  post({ type: 'ready', sampleRate: config.audio.sample_rate, threads: ort.env.wasm.numThreads ?? 1 })
}

async function synthesize(text: string): Promise<Float32Array> {
  if (!session || !config) throw new Error('Voice is not loaded.')
  const segments = splitOnPunctuation(text)
  const phonemes = await Promise.all(
    segments.map(async (segment) => (await phonemize(segment.text, config!.espeak.voice)).join(' ')),
  )
  const ids = phonemesToIds(joinPhonemes(segments, phonemes), config.phoneme_id_map)
  const { noise_scale, length_scale, noise_w } = config.inference

  const feeds: Record<string, ort.Tensor> = {
    input: new ort.Tensor('int64', BigInt64Array.from(ids, BigInt), [1, ids.length]),
    input_lengths: new ort.Tensor('int64', BigInt64Array.from([BigInt(ids.length)]), [1]),
    scales: new ort.Tensor('float32', Float32Array.from([noise_scale, length_scale, noise_w]), [3]),
  }
  if (config.num_speakers > 1) feeds.sid = new ort.Tensor('int64', BigInt64Array.from([0n]), [1])

  const output = await session.run(feeds)
  const audio = output[session.outputNames[0]!]!.data as Float32Array
  return Float32Array.from(audio) // own copy, safe to transfer
}

self.onmessage = (event: MessageEvent<ToWorker>) => {
  const message = event.data
  if (message.type === 'init') {
    ready ??= init(message.modelUrl, message.configUrl).catch((error: unknown) => {
      ready = null // allow a retry
      post({ type: 'error', message: error instanceof Error ? error.message : String(error), fatal: true })
      throw error
    })
    return
  }
  if (message.type === 'cancel') {
    cancelledBefore = Math.max(cancelledBefore, message.generation)
    return
  }

  const { id, generation, text } = message
  queue = queue.then(async () => {
    if (generation < cancelledBefore) return post({ type: 'skipped', id, generation })
    try {
      if (!ready) throw new Error('Voice is not loaded.')
      await ready
      const samples = await synthesize(text)
      if (generation < cancelledBefore) return post({ type: 'skipped', id, generation })
      post({ type: 'audio', id, generation, samples, sampleRate: config!.audio.sample_rate }, [
        samples.buffer,
      ])
    } catch (error) {
      post({
        type: 'error',
        message: error instanceof Error ? error.message : String(error),
        fatal: false,
        id,
        generation,
      })
    }
  })
}
