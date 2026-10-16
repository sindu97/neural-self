import { LIMITS } from '@/core/constants'

/** Files split into those to upload and those rejected, with the reason. */
export interface FileCheck {
  accepted: File[]
  rejected: { file: File; reason: string }[]
}

/** Quick client-side checks so obvious mistakes fail instantly; the server re-checks everything. */
export function validateFiles(files: Iterable<File>): FileCheck {
  const result: FileCheck = { accepted: [], rejected: [] }
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      result.rejected.push({ file, reason: 'Only PDF files are supported.' })
    } else if (file.size === 0) {
      result.rejected.push({ file, reason: 'The file is empty.' })
    } else if (file.size > LIMITS.maxUploadBytes) {
      result.rejected.push({ file, reason: 'The file is larger than 20 MB.' })
    } else {
      result.accepted.push(file)
    }
  }
  return result
}
