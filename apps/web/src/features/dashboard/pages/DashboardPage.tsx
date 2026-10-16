import { ArrowUpRight, CheckCircle2, FileText, MessageSquare } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { StatCard } from '@/components/layout/StatCard'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ROUTES } from '@/core/constants'
import { ActivityTimeline, useActivity } from '@/features/activity'
import { useCurrentUser } from '@/features/auth'
import { useConversations } from '@/features/chat'
import {
  DocumentList,
  DocumentListSkeleton,
  UploadButton,
  UploadProgressList,
  useDocumentLibrary,
  useRecentDocuments,
  useUploadDocuments,
} from '@/features/documents'
import { formatLongDate, greeting } from '@/lib/format'

const WEEK_MS = 7 * 24 * 3600 * 1000

/** Overview: greeting, upload banner, stats, recent documents and recent activity. */
export default function DashboardPage() {
  const user = useCurrentUser()
  const recent = useRecentDocuments(4)
  const library = useDocumentLibrary()
  const conversations = useConversations()
  const activity = useActivity(4)
  const { upload, uploads, isUploading } = useUploadDocuments()
  // Captured once: render must not depend on the clock (React purity rule).
  const [now] = useState(() => Date.now())

  const allDocuments = library.data?.pages.flatMap((page) => page.items) ?? []
  const totalDocuments = library.data?.pages[0]?.pagination.total ?? 0
  const readyCount = allDocuments.filter((document) => document.status === 'completed').length
  const addedThisWeek = allDocuments.filter(
    (document) => now - new Date(document.created_at).getTime() < WEEK_MS,
  ).length
  const firstName = user.name.split(' ')[0] ?? user.name

  return (
    <>
      <section className="mb-[27px] flex flex-col gap-2.5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="eyebrow mb-[11px]">Your personal knowledge space</div>
          <h1 className="text-[clamp(27px,3vw,36px)] leading-[1.14] font-bold tracking-[-1.25px]">
            {greeting()}, {firstName} <span className="text-[27px]">✦</span>
          </h1>
          <p className="mt-2.5 text-[13px] leading-relaxed text-muted-foreground">
            Your ideas, documents, and answers — all in one thoughtful place.
          </p>
        </div>
        <div className="hidden pb-1 text-[11px] whitespace-nowrap text-[#8991a2] uppercase sm:block">
          {formatLongDate()}
        </div>
      </section>

      <section className="bg-brand-gradient relative mb-[26px] flex items-center justify-between gap-6 overflow-hidden rounded-[19px] px-[21px] py-[23px] text-white shadow-hero sm:px-[30px] sm:py-[27px]">
        <span
          className="pointer-events-none absolute -top-[155px] right-[10%] size-[230px] rounded-full border border-white/15"
          aria-hidden
        />
        <span
          className="pointer-events-none absolute -top-[155px] -right-[30px] size-[290px] rounded-full border border-white/15"
          aria-hidden
        />
        <div className="relative z-[1] max-w-[500px]">
          <h2 className="mb-2 text-[20px] font-bold tracking-[-0.5px] sm:text-[22px]">
            A little more clarity, every day.
          </h2>
          <p className="mb-[19px] max-w-[410px] text-xs leading-[1.65] text-[#eeecff]">
            Bring your PDFs to life. Ask questions, discover connections, and get answers grounded in your own
            documents.
          </p>
          <div className="flex flex-wrap items-center gap-2.5">
            <UploadButton variant="inverse" onFiles={upload} disabled={isUploading} />
            <Button variant="glass" asChild>
              <Link to={ROUTES.chat}>
                Start a conversation <ArrowUpRight aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
        <HeroArt />
      </section>

      <UploadProgressList uploads={uploads} />

      <section className="mb-[30px] grid grid-cols-3 gap-[9px] sm:gap-[15px]">
        <StatCard
          label="Total documents"
          value={totalDocuments}
          icon={FileText}
          loading={library.isPending}
          note={
            addedThisWeek > 0 ? (
              <>
                <span className="font-bold text-success">+{addedThisWeek}</span> added this week
              </>
            ) : (
              'In your knowledge base'
            )
          }
        />
        <StatCard
          label="Ready to search"
          value={readyCount}
          icon={CheckCircle2}
          tone="success"
          loading={library.isPending}
          note="Documents indexed successfully"
        />
        <StatCard
          label="Conversations"
          value={conversations.data?.pagination.total ?? 0}
          icon={MessageSquare}
          tone="warning"
          loading={conversations.isPending}
          note="Across your knowledge base"
        />
      </section>

      <SectionHead
        title="Your documents"
        subtitle="Recently added to your knowledge base"
        to={ROUTES.documents}
        link="View all documents →"
      />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.65fr)_minmax(240px,0.9fr)]">
        <section>
          <div className="overflow-hidden rounded-[15px] border bg-card">
            {recent.isPending ? (
              <DocumentListSkeleton />
            ) : recent.isError ? (
              <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />
            ) : recent.data.items.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="Your shelf is empty"
                description="Upload a PDF to start searching and asking questions."
                action={<UploadButton onFiles={upload} label="Upload a PDF" />}
              />
            ) : (
              <DocumentList documents={recent.data.items} />
            )}
          </div>
        </section>

        <section className="hidden lg:block">
          <div className="overflow-hidden rounded-[15px] border bg-card">
            <div className="px-[19px] pt-[19px]">
              <SectionHead
                title="Recent activity"
                subtitle="A pulse on your workspace"
                to={ROUTES.activity}
                link="See all"
                inline
              />
            </div>
            <div className="p-5">
              {activity.isPending ? (
                <div className="space-y-4">
                  {Array.from({ length: 3 }, (_, index) => (
                    <Skeleton key={index} className="h-10" />
                  ))}
                </div>
              ) : activity.items.length === 0 ? (
                <p className="py-4 text-center text-xs text-muted-foreground">Nothing yet.</p>
              ) : (
                <ActivityTimeline items={activity.items} />
              )}
            </div>
          </div>
        </section>
      </div>
    </>
  )
}

function SectionHead({
  title,
  subtitle,
  to,
  link,
  inline,
}: {
  title: string
  subtitle: string
  to: string
  link: string
  inline?: boolean
}) {
  return (
    <div
      className={
        inline
          ? 'flex items-center justify-between gap-3'
          : 'mb-[15px] flex items-center justify-between gap-3'
      }
    >
      <div>
        <h3 className="text-[15px] font-bold tracking-[-0.35px] sm:text-base">{title}</h3>
        <div className="mt-1 text-[11px] text-muted-foreground">{subtitle}</div>
      </div>
      <Link to={to} className="py-[7px] text-[11px] font-bold text-primary hover:underline">
        {link}
      </Link>
    </div>
  )
}

/** The tilted document illustration from the design's banner. */
function HeroArt() {
  return (
    <div
      className="relative z-[1] hidden size-[112px] shrink-0 rotate-[5deg] place-items-center rounded-[32px] border border-white/25 bg-white/10 sm:grid lg:size-[142px]"
      aria-hidden
    >
      <div className="h-[105px] w-[90px] -rotate-[5deg] scale-[.85] rounded-xl bg-white px-3 py-[15px] shadow-[0_8px_20px_#4339a355] lg:scale-100">
        <div className="mb-2 h-[5px] w-[70%] rounded bg-[#a39af9]" />
        <div className="mb-2 h-[5px] w-full rounded bg-[#e8e6ff]" />
        <div className="mb-2 h-[5px] w-[82%] rounded bg-[#e8e6ff]" />
        <div className="mt-[13px] mb-2 h-[5px] w-[90%] rounded bg-[#e8e6ff]" />
        <div className="mb-2 h-[5px] w-[60%] rounded bg-[#e8e6ff]" />
        <span className="mt-1 inline-block rounded bg-[#e6fbf3] px-1.5 py-1 text-[7px] text-[#16865f]">
          ✓ Indexed
        </span>
      </div>
    </div>
  )
}
