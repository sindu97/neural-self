import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { describeError } from '@/lib/api/errors'

import * as chatApi from '../api/chat-api'

export const chatKeys = {
  all: ['conversations'] as const,
  list: ['conversations', 'list'] as const,
  detail: (id: string) => ['conversations', 'detail', id] as const,
  messages: (id: string) => ['conversations', 'messages', id] as const,
}

// One conversation rarely exceeds this; older history is still on the server.
const HISTORY_LIMIT = 100

/** The user's conversations (up to 100), most recently active first. */
export function useConversations() {
  return useQuery({
    queryKey: chatKeys.list,
    queryFn: () => chatApi.listConversations({ limit: 100 }),
  })
}

/** A conversation's history (up to 100 messages). Disabled until there is an id. */
export function useMessages(conversationId: string | undefined) {
  return useQuery({
    queryKey: chatKeys.messages(conversationId ?? ''),
    queryFn: () => chatApi.listMessages(conversationId!, { limit: HISTORY_LIMIT }),
    enabled: Boolean(conversationId),
  })
}

/** Create a conversation and refresh the conversation list. */
export function useCreateConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => chatApi.createConversation(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chatKeys.list }),
  })
}

/** Delete a conversation, drop its cached messages, refresh the list and confirm with a toast. */
export function useDeleteConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => chatApi.deleteConversation(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: chatKeys.messages(id) })
      toast.success('Conversation deleted.')
      return queryClient.invalidateQueries({ queryKey: chatKeys.list })
    },
    onError: (error) => toast.error(describeError(error)),
  })
}
