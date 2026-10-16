import { useMemo } from 'react'

import { useConversations } from '@/features/chat'
import { useDocumentLibrary } from '@/features/documents'

export type ActivityKind = 'uploaded' | 'indexed' | 'failed' | 'conversation'

/** One event in the activity timeline. */
export interface ActivityItem {
  id: string
  kind: ActivityKind
  title: string
  subject: string
  at: string
  href: string
}

/**
 * A timeline built from documents and conversations. The backend has no
 * activity log yet, so this shows what can be derived from their timestamps.
 */
export function useActivity(limit?: number) {
  const library = useDocumentLibrary()
  const conversations = useConversations()

  const items = useMemo(() => {
    const events: ActivityItem[] = []
    for (const document of library.data?.pages.flatMap((page) => page.items) ?? []) {
      events.push({
        id: `${document.id}-uploaded`,
        kind: 'uploaded',
        title: 'New document uploaded',
        subject: document.filename,
        at: document.created_at,
        href: '/documents',
      })
      if (document.status === 'completed' && document.updated_at) {
        events.push({
          id: `${document.id}-indexed`,
          kind: 'indexed',
          title: 'Document indexed',
          subject: document.filename,
          at: document.updated_at,
          href: '/documents',
        })
      }
      if (document.status === 'failed' && document.updated_at) {
        events.push({
          id: `${document.id}-failed`,
          kind: 'failed',
          title: 'Processing failed',
          subject: document.filename,
          at: document.updated_at,
          href: '/documents',
        })
      }
    }
    for (const conversation of conversations.data?.items ?? []) {
      events.push({
        id: `${conversation.id}-created`,
        kind: 'conversation',
        title: 'Conversation started',
        subject: conversation.title ?? 'New conversation',
        at: conversation.created_at,
        href: `/chat/${conversation.id}`,
      })
    }
    events.sort((a, b) => b.at.localeCompare(a.at))
    return limit ? events.slice(0, limit) : events
  }, [library.data, conversations.data, limit])

  return {
    items,
    isPending: library.isPending || conversations.isPending,
    isError: library.isError || conversations.isError,
    error: library.error ?? conversations.error,
  }
}
