import { CheckCircle2 } from 'lucide-react'
import type { ReactNode } from 'react'

import { BrandLogo } from '@/components/brand/BrandLogo'

const POINTS = [
  'Upload PDFs and search them by meaning',
  'Ask questions and get answers with sources',
  'Your documents stay private to your account',
]

/** Two-column layout for login and signup: brand panel and form. */
export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <aside className="bg-brand-gradient relative hidden overflow-hidden p-12 text-white lg:flex lg:flex-col">
        <div className="pointer-events-none absolute -top-40 right-[10%] size-[230px] rounded-full border border-white/15" />
        <div className="pointer-events-none absolute -top-40 -right-8 size-[290px] rounded-full border border-white/15" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 size-[320px] rounded-full border border-white/10" />

        <div className="relative flex items-center gap-3">
          <div className="grid size-[38px] place-items-center rounded-[13px] bg-white/15 ring-1 ring-white/30">
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
          <span className="text-[19px] font-bold tracking-[-0.5px]">NeuralShelf</span>
        </div>

        <div className="relative mt-auto max-w-md">
          <h2 className="text-[30px] leading-tight font-bold tracking-[-0.8px]">
            A little more clarity, every day.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-white/85">
            Bring your PDFs to life. Ask questions, discover connections, and get answers grounded in your own
            documents.
          </p>
          <ul className="mt-8 space-y-3">
            {POINTS.map((point) => (
              <li key={point} className="flex items-center gap-3 text-sm text-white/90">
                <CheckCircle2 className="size-4 shrink-0" aria-hidden />
                {point}
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <main className="flex flex-col justify-center px-5 py-10 sm:px-12">
        <div className="mx-auto w-full max-w-[400px]">
          <BrandLogo className="mb-10 lg:hidden" />
          <div className="eyebrow mb-2.5">Your personal knowledge space</div>
          <h1 className="text-[28px] leading-tight font-bold tracking-[-0.9px]">{title}</h1>
          <p className="mt-2 mb-8 text-[13px] text-muted-foreground">{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  )
}
