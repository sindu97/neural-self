/**
 * Text -> phoneme IDs for Piper voices, mirroring piper-phonemize:
 * espeak-ng IPA phonemes, with punctuation kept as phonemes (it drives pauses
 * and intonation), mapped through the voice's phoneme_id_map as
 * BOS, PAD, (phoneme, PAD)*, EOS.
 */

/** The parts of a Piper voice's `.onnx.json` config used for synthesis. */
export interface PiperVoiceConfig {
  audio: { sample_rate: number }
  espeak: { voice: string }
  inference: { noise_scale: number; length_scale: number; noise_w: number }
  num_speakers: number
  phoneme_id_map: Record<string, number[]>
}

const BOS = '^'
const EOS = '$'
const PAD = '_'

/** A run of text and the punctuation that ends it. */
export interface TextSegment {
  text: string
  punctuation: string
}

/**
 * Split text into runs ending in punctuation. Punctuation only counts when
 * followed by whitespace or the end, so "3.14" stays one number.
 */
export function splitOnPunctuation(text: string): TextSegment[] {
  const segments: TextSegment[] = []
  for (const match of text.matchAll(/(.+?)([.,;:!?]+)(?=\s|$)|(\S.*$)/g)) {
    const body = (match[1] ?? match[3] ?? '').trim()
    if (body) segments.push({ text: body, punctuation: match[2] ?? '' })
  }
  return segments
}

/** Join per-segment phonemes back together with their punctuation. */
export function joinPhonemes(segments: TextSegment[], phonemes: string[]): string {
  return segments.map((segment, index) => `${phonemes[index] ?? ''}${segment.punctuation}`).join(' ')
}

/** Map phonemes to the voice's input ids: BOS, PAD, (phoneme, PAD)…, EOS. Unknown phonemes are skipped. */
export function phonemesToIds(phonemes: string, idMap: Record<string, number[]>): number[] {
  const pad = idMap[PAD] ?? [0]
  const ids = [...(idMap[BOS] ?? []), ...pad]
  for (const phoneme of phonemes) {
    const mapped = idMap[phoneme]
    if (mapped) ids.push(...mapped, ...pad) // characters the voice doesn't know are skipped
  }
  ids.push(...(idMap[EOS] ?? []))
  return ids
}
