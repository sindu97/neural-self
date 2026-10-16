/** Messages between the app and the Piper worker. */

export type ToWorker =
  | { type: 'init'; modelUrl: string; configUrl: string }
  /** `generation` lets the app cancel everything older in one step. */
  | { type: 'synthesize'; id: number; generation: number; text: string }
  | { type: 'cancel'; generation: number }

export type FromWorker =
  | { type: 'progress'; loaded: number; total: number }
  | { type: 'ready'; sampleRate: number; threads: number }
  | { type: 'audio'; id: number; generation: number; samples: Float32Array; sampleRate: number }
  | { type: 'skipped'; id: number; generation: number }
  | { type: 'error'; message: string; fatal: boolean; id?: number; generation?: number }
