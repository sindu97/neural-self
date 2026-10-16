import { AlertCircle } from 'lucide-react'

/** Error banner shown above a form. */
export function FormAlert({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-[10px] border border-destructive/20 bg-destructive-soft px-3.5 py-3 text-xs text-destructive"
    >
      <AlertCircle className="mt-px size-4 shrink-0" aria-hidden />
      <span>{message}</span>
    </div>
  )
}
