import { MessageSquare, MoreHorizontal, Plus, Trash2 } from 'lucide-react'
import { NavLink } from 'react-router'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { ROUTES } from '@/core/constants'
import { formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'

import { useConversations } from '../hooks/use-conversations'

/** The user's conversations, with a New chat button and a delete action per item. */
export function ConversationList({
  onNewChat,
  onDelete,
  onNavigate,
}: {
  onNewChat: () => void
  onDelete: (id: string) => void
  onNavigate?: () => void
}) {
  const conversations = useConversations()
  const items = conversations.data?.items ?? []

  return (
    <div className="flex h-full flex-col">
      <Button onClick={onNewChat} className="mb-4 w-full">
        <Plus aria-hidden /> New chat
      </Button>
      <div className="mb-2 px-1 text-[10px] font-bold tracking-[0.14em] text-subtle">RECENT</div>
      <nav className="-mx-1 flex-1 space-y-1 overflow-y-auto px-1" aria-label="Conversations">
        {conversations.isPending &&
          Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-12 rounded-[10px]" />)}
        {!conversations.isPending && items.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">No conversations yet.</p>
        )}
        {items.map((conversation) => (
          <div key={conversation.id} className="group relative">
            <NavLink
              to={ROUTES.conversation(conversation.id)}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'flex items-start gap-2.5 rounded-[10px] px-2.5 py-2.5 pr-9 text-xs text-sidebar-foreground hover:bg-muted',
                  isActive && 'bg-accent font-semibold text-primary hover:bg-accent',
                )
              }
            >
              <MessageSquare className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              <span className="min-w-0">
                <span className="block truncate">{conversation.title ?? 'New conversation'}</span>
                <span className="mt-0.5 block text-[10px] font-normal text-subtle">
                  {formatRelativeTime(conversation.updated_at)}
                </span>
              </span>
            </NavLink>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  className="absolute top-2.5 right-1.5 text-subtle opacity-0 group-hover:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100"
                  aria-label={`Options for ${conversation.title ?? 'conversation'}`}
                >
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem variant="destructive" onSelect={() => onDelete(conversation.id)}>
                  <Trash2 /> Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ))}
      </nav>
    </div>
  )
}
