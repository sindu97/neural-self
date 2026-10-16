import { Activity, FileText, LayoutGrid, MessageSquare, Search, ServerCog, Settings } from 'lucide-react'

import { ROUTES } from '@/core/constants'

/** One sidebar link; `count` shows the number of documents or conversations. */
export interface NavItem {
  to: string
  label: string
  icon: typeof LayoutGrid
  count?: 'documents' | 'conversations'
  end?: boolean
}

export const WORKSPACE_NAV: NavItem[] = [
  { to: ROUTES.overview, label: 'Overview', icon: LayoutGrid, end: true },
  { to: ROUTES.documents, label: 'Documents', icon: FileText, count: 'documents' },
  { to: ROUTES.chat, label: 'AI Chat', icon: MessageSquare, count: 'conversations' },
  { to: ROUTES.search, label: 'Semantic Search', icon: Search },
]

export const MANAGE_NAV: NavItem[] = [
  { to: ROUTES.activity, label: 'Activity', icon: Activity },
  { to: ROUTES.settings, label: 'Settings', icon: Settings },
]

export const ADMIN_NAV: NavItem[] = [{ to: ROUTES.adminJobs, label: 'Ingestion jobs', icon: ServerCog }]

/** Breadcrumb label for the current path. */
export function pageTitle(pathname: string): string {
  const all = [...WORKSPACE_NAV, ...MANAGE_NAV, ...ADMIN_NAV]
  const match = all
    .filter((item) => (item.end ? pathname === item.to : pathname.startsWith(item.to)))
    .sort((a, b) => b.to.length - a.to.length)[0]
  return match?.label ?? 'Overview'
}
