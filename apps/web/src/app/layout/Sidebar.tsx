import { LogOut, MoreHorizontal, Settings } from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router'

import { BrandLogo } from '@/components/brand/BrandLogo'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ROUTES } from '@/core/constants'
import { useAuth, useCurrentUser } from '@/features/auth'
import { useConversations } from '@/features/chat'
import { useRecentDocuments } from '@/features/documents'
import { initials } from '@/lib/format'
import { cn } from '@/lib/utils'

import { ADMIN_NAV, MANAGE_NAV, type NavItem, WORKSPACE_NAV } from './nav-items'

/** Main navigation: brand, workspace, nav groups (admin only for admins) and the account menu. */
export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const user = useCurrentUser()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const documents = useRecentDocuments(1)
  const conversations = useConversations()

  const counts = {
    documents: documents.data?.pagination.total,
    conversations: conversations.data?.pagination.total,
  }

  return (
    <div className="flex h-full flex-col gap-[30px] px-[17px] py-[26px]">
      <BrandLogo className="px-2.5" />

      <div className="mx-2 flex items-center gap-2.5 rounded-[13px] border px-[13px] py-3">
        <div className="grid size-8 shrink-0 place-items-center rounded-[10px] bg-[#f2f0ff] font-bold text-primary">
          {user.name[0]?.toUpperCase() ?? 'N'}
        </div>
        <div className="min-w-0">
          <strong className="block text-xs">My workspace</strong>
          <small className="block truncate text-[11px] text-muted-foreground">Personal knowledge base</small>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-[30px] overflow-y-auto">
        <NavGroup label="WORKSPACE" items={WORKSPACE_NAV} counts={counts} onNavigate={onNavigate} />
        <NavGroup label="MANAGE" items={MANAGE_NAV} counts={counts} onNavigate={onNavigate} />
        {user.is_admin && (
          <NavGroup label="ADMIN" items={ADMIN_NAV} counts={counts} onNavigate={onNavigate} />
        )}
      </div>

      <div>
        <div className="bg-brand-soft mx-[5px] mb-5 rounded-[15px] border border-[#e8e3ff] px-[15px] py-[17px]">
          <div className="text-xl text-primary">✳</div>
          <strong className="mt-2 mb-[5px] block text-xs">Your knowledge, amplified</strong>
          <p className="mb-3 text-[11px] leading-[1.55] text-[#777b91]">
            Ask questions across your documents and find answers with sources you can trust.
          </p>
          <Link
            to={ROUTES.chat}
            onClick={onNavigate}
            className="block w-full rounded-lg bg-white px-2.5 py-[9px] text-center text-[11px] font-bold text-primary hover:bg-white/80"
          >
            Explore AI Chat ↗
          </Link>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger className="flex w-full items-center gap-2.5 border-t px-[9px] pt-3.5 text-left outline-none">
            <div className="grid size-[34px] shrink-0 place-items-center rounded-full bg-[#fce5d6] text-xs font-bold text-[#9b5a34]">
              {initials(user.name)}
            </div>
            <div className="min-w-0 flex-1">
              <strong className="block truncate text-xs">{user.name}</strong>
              <small className="block truncate text-[10px] text-muted-foreground">{user.email}</small>
            </div>
            <MoreHorizontal className="size-4 text-subtle" aria-hidden />
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-56">
            <DropdownMenuLabel className="text-xs">
              {user.is_admin ? 'Administrator' : 'Member'}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate(ROUTES.settings)}>
              <Settings /> Settings
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onSelect={async () => {
                await logout()
                navigate(ROUTES.login, { replace: true })
              }}
            >
              <LogOut /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}

function NavGroup({
  label,
  items,
  counts,
  onNavigate,
}: {
  label: string
  items: NavItem[]
  counts: Record<'documents' | 'conversations', number | undefined>
  onNavigate?: () => void
}) {
  return (
    <div>
      <div className="mb-2 px-[13px] text-[10px] font-bold tracking-[1.4px] text-[#a1a8b6]">{label}</div>
      <nav className="grid gap-[5px]" aria-label={label.toLowerCase()}>
        {items.map((item) => {
          const count = item.count ? counts[item.count] : undefined
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-[10px] px-[13px] py-[11px] text-[13px] text-sidebar-foreground hover:bg-muted',
                  isActive &&
                    'bg-sidebar-accent font-semibold text-sidebar-accent-foreground hover:bg-sidebar-accent',
                )
              }
            >
              <item.icon className="size-[18px]" strokeWidth={1.8} aria-hidden />
              {item.label}
              {count !== undefined && count > 0 && (
                <span className="ml-auto rounded-[7px] border bg-white px-1.5 py-0.5 text-[10px] font-normal text-[#7c8496]">
                  {count}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}
