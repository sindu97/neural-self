import { joinPhonemes, phonemesToIds, splitOnPunctuation } from './phonemes'

describe('splitOnPunctuation', () => {
  it('keeps punctuation with each run', () => {
    expect(splitOnPunctuation('Hello, world! Is 3.14 pi?')).toEqual([
      { text: 'Hello', punctuation: ',' },
      { text: 'world', punctuation: '!' },
      { text: 'Is 3.14 pi', punctuation: '?' },
    ])
  })

  it('keeps a trailing run without punctuation', () => {
    expect(splitOnPunctuation('First part. and the rest')).toEqual([
      { text: 'First part', punctuation: '.' },
      { text: 'and the rest', punctuation: '' },
    ])
  })
})

describe('phonemes to ids', () => {
  const idMap = { _: [0], '^': [1], $: [2], ' ': [3], a: [10], b: [11], ',': [8] }

  it('wraps in BOS/EOS and pads every phoneme, skipping unknown ones', () => {
    expect(phonemesToIds('ab, x', idMap)).toEqual([1, 0, 10, 0, 11, 0, 8, 0, 3, 0, 2])
  })

  it('joins segment phonemes with their punctuation', () => {
    expect(
      joinPhonemes(
        [
          { text: 'Hello', punctuation: ',' },
          { text: 'world', punctuation: '.' },
        ],
        ['həlˈoʊ', 'wˈɜːld'],
      ),
    ).toBe('həlˈoʊ, wˈɜːld.')
  })
})
