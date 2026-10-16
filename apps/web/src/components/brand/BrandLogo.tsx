import { cn } from '@/lib/utils'

/** The NeuralShelf mark and wordmark from the design. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'bg-brand-mark grid size-[38px] place-items-center rounded-[13px] text-white shadow-[0_7px_16px_#6658e833]',
        className,
      )}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        className="w-[23px]"
        aria-hidden
      >
        <path d="M6 4.5h8.5L19 9v10.5H6z" />
        <path d="M14 4.5V9h5M9 12h7M9 15h5" />
        <path d="M3 7v14h13" opacity=".65" />
      </svg>
    </div>
  )
}

/** Brand mark with the NeuralShelf wordmark and, optionally, the tagline. */
export function BrandLogo({ className, subtitle = true }: { className?: string; subtitle?: boolean }) {
  return (
    <div className={cn('flex items-center gap-[11px]', className)}>
      <BrandMark />
      <div>
        <div className="text-[19px] leading-tight font-bold tracking-[-0.5px]">NeuralShelf</div>
        {subtitle && (
          <div className="mt-0.5 text-[9px] tracking-[1.3px] whitespace-nowrap text-subtle">
            YOUR KNOWLEDGE, CONNECTED
          </div>
        )}
      </div>
    </div>
  )
}
