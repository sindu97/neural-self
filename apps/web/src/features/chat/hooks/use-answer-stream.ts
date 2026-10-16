import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'

import { toApiError } from '@/lib/api/errors'
import type { ChatMessage, Citation, Exchange, MessageCreateRequest, Page } from '@/lib/api/types'

import { streamAnswer } from '../api/chat-api'
import { chatKeys } from './use-conversations'

/** Follow an answer as it streams, e.g. to read it aloud. */
export interface AnswerListener {
  onToken?: (delta: string) => void
  onDone?: (exchange: Exchange) => void
  /** Failed or stopped: nothing was saved. */
  onAbort?: () => void
}

/** The question being answered and the answer so far, until it is saved. */
export interface PendingTurn {
  conversationId: string
  question: string
  answer: string
  citations: Citation[]
  status: 'streaming' | 'error'
  error?: string
}

/**
 * Streams one answer at a time. While it streams, `pending` holds the
 * question and the partial answer; when the server sends `done`, both saved
 * messages are added to the conversation's cached history and `pending` clears.
 */
export function useAnswerStream() {
  const queryClient = useQueryClient()
  const [pending, setPending] = useState<PendingTurn | null>(null)
  const controller = useRef<AbortController | null>(null)

  const ask = useCallback(
    async (conversationId: string, request: MessageCreateRequest, listener: AnswerListener = {}) => {
      controller.current?.abort()
      const abort = new AbortController()
      controller.current = abort
      setPending({
        conversationId,
        question: request.content,
        answer: '',
        citations: [],
        status: 'streaming',
      })

      const fail = (message: string) => {
        listener.onAbort?.()
        setPending((turn) => (turn ? { ...turn, status: 'error', error: message } : turn))
      }

      try {
        for await (const { event, data } of streamAnswer(conversationId, request, abort.signal)) {
          if (event === 'start') {
            const { citations } = data as { citations: Citation[] }
            setPending((turn) => (turn ? { ...turn, citations } : turn))
          } else if (event === 'token') {
            const { delta } = data as { delta: string }
            listener.onToken?.(delta)
            setPending((turn) => (turn ? { ...turn, answer: turn.answer + delta } : turn))
          } else if (event === 'done') {
            const exchange = data as Exchange
            listener.onDone?.(exchange)
            queryClient.setQueryData<Page<ChatMessage>>(chatKeys.messages(conversationId), (page) =>
              page
                ? {
                    items: [...page.items, exchange.user_message, exchange.assistant_message],
                    pagination: { ...page.pagination, total: page.pagination.total + 2 },
                  }
                : page,
            )
            void queryClient.invalidateQueries({ queryKey: chatKeys.messages(conversationId) })
            void queryClient.invalidateQueries({ queryKey: chatKeys.list })
            setPending(null)
          } else if (event === 'error') {
            fail((data as { message: string }).message)
          }
        }
      } catch (error) {
        if (abort.signal.aborted) {
          listener.onAbort?.()
          setPending(null) // stopped by the user: nothing was saved
          return
        }
        fail(toApiError(error).message)
      }
    },
    [queryClient],
  )

  const stop = useCallback(() => controller.current?.abort(), [])
  const dismiss = useCallback(() => setPending(null), [])

  return { pending, ask, stop, dismiss, isStreaming: pending?.status === 'streaming' }
}
