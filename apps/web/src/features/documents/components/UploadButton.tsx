import { Upload } from 'lucide-react'
import { useRef } from 'react'

import { Button } from '@/components/ui/button'

/** Button that opens a file picker for one or more PDFs. */
export function UploadButton({
  onFiles,
  variant = 'default',
  label = 'Upload documents',
  disabled,
}: {
  onFiles: (files: File[]) => void
  variant?: 'default' | 'inverse' | 'outline'
  label?: string
  disabled?: boolean
}) {
  const input = useRef<HTMLInputElement>(null)
  return (
    <>
      <Button variant={variant} onClick={() => input.current?.click()} disabled={disabled}>
        <Upload aria-hidden /> {label}
      </Button>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        hidden
        onChange={(event) => {
          const files = Array.from(event.target.files ?? [])
          event.target.value = '' // allow choosing the same file again
          if (files.length) onFiles(files)
        }}
      />
    </>
  )
}
