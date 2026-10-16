import { BrandMark } from '@/components/brand/BrandLogo'

/** Full-screen loading state, e.g. while the session is being restored. */
export function FullPageLoader() {
  return (
    <div className="grid min-h-screen place-items-center bg-background" role="status" aria-live="polite">
      <div className="flex flex-col items-center gap-4">
        <BrandMark className="animate-pulse" />
        <span className="text-xs text-muted-foreground">Loading your shelf…</span>
      </div>
    </div>
  )
}
