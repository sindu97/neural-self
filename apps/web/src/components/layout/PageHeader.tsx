import type { ReactNode } from 'react'

/** Page title block in the design's "welcome" style. */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <section className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <div className="eyebrow mb-2.5">{eyebrow}</div>}
        <h1 className="text-[clamp(26px,3vw,34px)] leading-[1.14] font-bold tracking-[-1.1px]">{title}</h1>
        {description && (
          <p className="mt-2.5 text-[13px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </section>
  )
}
