/**
 * Splitting a streaming answer into speakable pieces (from the AI-tutor POC).
 *
 * Each piece is synthesized as one unit, so the answer is spoken a sentence
 * at a time while the rest is still streaming in.
 */

/** Fragments shorter than this are merged into the next sentence. */
const MIN_SPEECH_CHARS = 12

/**
 * Pull every complete sentence off the front of a growing buffer.
 *
 * A terminator only counts when whitespace follows it: that proves the
 * sentence is finished mid-stream and keeps "3.14" in one piece. The
 * unterminated tail stays in `rest` until more text arrives.
 */
export function drainSentences(buffer: string): { sentences: string[]; rest: string } {
  const sentences: string[] = []
  const boundary = /[.!?]+["')\]]*(?=\s)/g
  let rest = buffer
  let searchFrom = 0

  for (;;) {
    boundary.lastIndex = searchFrom
    const match = boundary.exec(rest)
    if (!match) break

    const end = match.index + match[0].length
    const candidate = rest.slice(0, end).trim()
    if (candidate.length < MIN_SPEECH_CHARS) {
      searchFrom = end // too short: keep it and speak it with the next sentence
      continue
    }
    sentences.push(candidate)
    rest = rest.slice(end)
    searchFrom = 0
  }
  return { sentences, rest }
}

// The first piece spoken is a short phrase, not a whole sentence, so audio
// starts sooner: a clause boundary after ~14 chars, or a word end after ~22.
const OPENING_CLAUSE = /^[\s\S]{14,}?[,;:—-](?=\s)/
const OPENING_WORDS = /^[\s\S]{22,}?\S(?=\s)/

/** A short opening phrase to speak before the first sentence is complete, so audio starts sooner. */
export function takeFirstFragment(buffer: string): { fragment: string; rest: string } | null {
  const match = OPENING_CLAUSE.exec(buffer) ?? OPENING_WORDS.exec(buffer)
  if (!match) return null
  return { fragment: match[0].trim(), rest: buffer.slice(match[0].length) }
}

/** Remove what shouldn't be read aloud: citation markers, markdown, links. */
export function cleanForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, ' ') // code blocks
    .replace(/\[(\d+)\](\[\d+\])*/g, '') // citation markers [1][2]
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [label](url) -> label
    .replace(/https?:\/\/\S+/g, '') // bare URLs
    .replace(/[*_`#>~|]/g, '') // markdown symbols
    .replace(/^\s*[-+]\s+/gm, '') // list bullets
    .replace(/[ \t]+/g, ' ')
}
