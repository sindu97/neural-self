import { AlertCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import Markdown from 'react-markdown'

import { BrandMark } from '@/components/brand/BrandLogo'
import type { Citation } from '@/lib/api/types'
import { cn } from '@/lib/utils'

import { Citations } from './Citations'

/** The user's question, right-aligned. */
export function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap text-primary-foreground">
        {content}
      </div>
    </div>
  )
}

/**
 * An answer: rendered markdown (never raw HTML), sources, and optional actions such as Listen.
 *
 * @remarks
 * While streaming it shows a caret, or typing dots before the first words.
 */
export function AssistantBubble({
  content,
  citations,
  streaming = false,
  error,
  actions,
}: {
  content: string
  citations: Citation[]
  streaming?: boolean
  error?: string
  /** E.g. the Listen / Mute button. */
  actions?: ReactNode
}) {
  return (
    <div className="flex gap-3">
      <BrandMark className="size-8 shrink-0 rounded-[10px] [&_svg]:w-[18px]" />
      <div className="min-w-0 max-w-[85%] flex-1 rounded-2xl rounded-tl-md border bg-card px-4 py-3 shadow-card">
        {content ? (
          // Model output is untrusted: react-markdown never renders raw HTML.
          <div
            className={cn(
              'prose-chat text-[13px] leading-relaxed',
              streaming &&
                'after:ml-0.5 after:inline-block after:h-3.5 after:w-1.5 after:animate-pulse after:bg-primary/60 after:align-middle',
            )}
          >
            <Markdown>{content}</Markdown>
          </div>
        ) : streaming ? (
          <TypingDots />
        ) : null}
        {error && (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-destructive" role="alert">
            <AlertCircle className="size-3.5" aria-hidden /> {error}
          </p>
        )}
        {!streaming && <Citations citations={citations} />}
        {actions && <div className="mt-2 -mb-1 -ml-2 flex items-center">{actions}</div>}
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <span className="flex gap-1 py-1.5" aria-label="Generating answer">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-1.5 animate-bounce rounded-full bg-primary/50"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  )
}
