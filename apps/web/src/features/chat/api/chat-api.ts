import { getOne, getPage, postOne, remove } from '@/lib/api/client'
import { streamEvents } from '@/lib/api/sse'
import type { ChatMessage, Conversation, MessageCreateRequest, Page, PageParams } from '@/lib/api/types'

/** The user's conversations, most recently active first. */
export function listConversations(params: PageParams = {}): Promise<Page<Conversation>> {
  return getPage<Conversation>('/conversations', { params })
}

/** One conversation's details. */
export function getConversation(id: string): Promise<Conversation> {
  return getOne<Conversation>(`/conversations/${id}`)
}

/** Create a conversation. Without a title, the first question becomes the title. */
export function createConversation(title?: string): Promise<Conversation> {
  return postOne<Conversation>('/conversations', title ? { title } : {})
}

/** Delete a conversation and all its messages. */
export function deleteConversation(id: string): Promise<void> {
  return remove(`/conversations/${id}`)
}

/** A page of a conversation's messages, oldest first. */
export function listMessages(id: string, params: PageParams = {}): Promise<Page<ChatMessage>> {
  return getPage<ChatMessage>(`/conversations/${id}/messages`, { params })
}

/** Ask a question and receive the answer as Server-Sent Events. */
export function streamAnswer(conversationId: string, request: MessageCreateRequest, signal?: AbortSignal) {
  return streamEvents(`/conversations/${conversationId}/messages/stream`, request, signal)
}
