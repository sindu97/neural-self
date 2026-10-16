import { validateFiles } from './validate-files'

const file = (name: string, size: number) =>
  new File([new Uint8Array(size)], name, { type: 'application/pdf' })

describe('validateFiles', () => {
  it('accepts PDFs and explains every rejection', () => {
    const result = validateFiles([
      file('ok.pdf', 10),
      file('UPPER.PDF', 10),
      file('notes.txt', 10),
      file('empty.pdf', 0),
      file('huge.pdf', 21 * 1024 * 1024),
    ])

    expect(result.accepted.map((f) => f.name)).toEqual(['ok.pdf', 'UPPER.PDF'])
    expect(result.rejected.map((r) => [r.file.name, r.reason])).toEqual([
      ['notes.txt', 'Only PDF files are supported.'],
      ['empty.pdf', 'The file is empty.'],
      ['huge.pdf', 'The file is larger than 20 MB.'],
    ])
  })
})
