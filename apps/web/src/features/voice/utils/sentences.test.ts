import { cleanForSpeech, drainSentences, takeFirstFragment } from './sentences'

describe('drainSentences', () => {
  it('returns complete sentences and keeps the unfinished tail', () => {
    const { sentences, rest } = drainSentences('Photosynthesis happens in leaves. It needs light. And wat')
    expect(sentences).toEqual(['Photosynthesis happens in leaves.', 'It needs light.'])
    expect(rest).toBe(' And wat')
  })

  it('waits for whitespace, so decimals and unfinished text stay whole', () => {
    expect(drainSentences('The value of pi is 3.14').sentences).toEqual([])
    expect(drainSentences('It is about 3.14 overall. Next').sentences).toEqual(['It is about 3.14 overall.'])
  })

  it('merges very short sentences into the next one', () => {
    expect(drainSentences('Yes. That is correct here. ').sentences).toEqual(['Yes. That is correct here.'])
  })
})

describe('takeFirstFragment', () => {
  it('cuts at an early clause boundary', () => {
    expect(takeFirstFragment('Photosynthesis, simply put, is how plants')).toEqual({
      fragment: 'Photosynthesis,',
      rest: ' simply put, is how plants',
    })
  })

  it('waits until there is enough text', () => {
    expect(takeFirstFragment('Short start')).toBeNull()
  })
})

describe('cleanForSpeech', () => {
  it('drops citations, markdown and links', () => {
    expect(
      cleanForSpeech('It happens in **chloroplasts** [1][2]. See [notes](https://x.y) or https://a.b'),
    ).toBe('It happens in chloroplasts . See notes or ')
  })
})
