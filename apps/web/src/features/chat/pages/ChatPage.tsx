import { FileText, ListIcon, RotateCcw, Sparkles, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { BrandMark } from '@/components/brand/BrandLogo'
import { ErrorState } from '@/components/feedback/ErrorState'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { ROUTES } from '@/core/constants'
import { useDocumentLibrary } from '@/features/documents'
import { AnswerVoiceButton, ReadAloudToggle, useVoice } from '@/features/voice'
import { describeError } from '@/lib/api/errors'

import { Composer, type SendOptions } from '../components/Composer'
import { ConversationList } from '../components/ConversationList'
import { AssistantBubble, UserBubble } from '../components/MessageBubble'
import { useAnswerStream } from '../hooks/use-answer-stream'
import { useCreateConversation, useDeleteConversation, useMessages } from '../hooks/use-conversations'

const ALL_DOCUMENTS = 'all'
/** Voice key for the answer still streaming (it has no message id yet). */
const STREAMING_ANSWER = 'streaming-answer'
const SUGGESTIONS = [
  'Summarise the key points of my latest document',
  'What are the main definitions I should know?',
  'List any dates or deadlines mentioned',
]

/**
 * AI chat: conversation list, message thread with streamed answers, scope selector and composer.
 *
 * @remarks
 * One route with an optional id (`/chat/:conversationId?`), so a new chat keeps its stream when it gets its id.
 */
export default function ChatPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const scope = params.get('document') ?? ALL_DOCUMENTS

  const messages = useMessages(conversationId)
  const stream = useAnswerStream()
  const createConversation = useCreateConversation()
  const deleteConversation = useDeleteConversation()
  const [listOpen, setListOpen] = useState(false)
  const { state: voiceState, voice } = useVoice()

  // Leaving the chat silences any answer being read aloud.
  useEffect(() => () => voice.stop(), [voice])

  const library = useDocumentLibrary()
  const readyDocuments = useMemo(
    () => (library.data?.pages.flatMap((page) => page.items) ?? []).filter((d) => d.status === 'completed'),
    [library.data],
  )
  const noDocuments = library.isSuccess && readyDocuments.length === 0

  const pending = stream.pending && stream.pending.conversationId === conversationId ? stream.pending : null
  const history = messages.data?.items ?? []
  const isEmpty = !conversationId || (messages.isSuccess && history.length === 0 && !pending)

  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [history.length, pending?.answer, pending?.status])

  const send = async (question: string, { byVoice }: SendOptions = { byVoice: false }) => {
    // Spoken questions get spoken answers; typed ones only with "Read answers aloud".
    const readAloud = byVoice || voice.getSnapshot().autoRead
    if (readAloud) voice.startAnswer(STREAMING_ANSWER)
    else voice.stop()

    let id = conversationId
    if (!id) {
      try {
        id = (await createConversation.mutateAsync()).id
      } catch (error) {
        toast.error(describeError(error))
        return
      }
      navigate({ pathname: ROUTES.conversation(id), search: params.toString() })
    }
    void stream.ask(
      id,
      {
        content: question,
        top_k: 5,
        document_ids: scope === ALL_DOCUMENTS ? [] : [scope],
      },
      readAloud
        ? {
            // Speech starts with the first sentence, while the rest streams in.
            onToken: (delta) => voice.append(STREAMING_ANSWER, delta),
            onDone: (exchange) => {
              voice.finish(STREAMING_ANSWER)
              voice.rekey(STREAMING_ANSWER, exchange.assistant_message.id)
            },
            onAbort: () => voice.getSnapshot().speakingKey === STREAMING_ANSWER && voice.stop(),
          }
        : undefined,
    )
  }

  const onDelete = (id: string) => {
    deleteConversation.mutate(id, {
      onSuccess: () => {
        if (id === conversationId) navigate(ROUTES.chat)
      },
    })
  }

  const newChat = () => {
    stream.stop()
    voice.stop()
    setListOpen(false)
    navigate(ROUTES.chat)
  }

  const conversationList = (
    <ConversationList onNewChat={newChat} onDelete={onDelete} onNavigate={() => setListOpen(false)} />
  )

  return (
    <div className="flex h-[calc(100dvh-7.5rem)] gap-5 lg:h-[calc(100dvh-8.75rem)]">
      <aside className="hidden w-64 shrink-0 rounded-[15px] border bg-card p-4 lg:block">
        {conversationList}
      </aside>

      <Sheet open={listOpen} onOpenChange={setListOpen}>
        <SheetContent side="left" className="w-72 p-4">
          <SheetHeader className="p-0 pb-4">
            <SheetTitle>Conversations</SheetTitle>
          </SheetHeader>
          {conversationList}
        </SheetContent>
      </Sheet>

      <section className="flex min-w-0 flex-1 flex-col">
        <div className="mb-3 flex items-center gap-2 lg:hidden">
          <Button variant="outline" size="sm" onClick={() => setListOpen(true)}>
            <ListIcon aria-hidden /> Conversations
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto pr-1" aria-live="polite">
          {conversationId && messages.isPending ? (
            <div className="space-y-4">
              <Skeleton className="ml-auto h-10 w-1/2 rounded-2xl" />
              <Skeleton className="h-24 w-3/4 rounded-2xl" />
            </div>
          ) : conversationId && messages.isError ? (
            <div className="rounded-[15px] border bg-card">
              <ErrorState error={messages.error} onRetry={() => void messages.refetch()} />
            </div>
          ) : isEmpty && !pending ? (
            <NewChatIntro noDocuments={noDocuments} onPick={(question) => void send(question)} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-5 pb-4">
              {history.map((message) =>
                message.role === 'user' ? (
                  <UserBubble key={message.id} content={message.content} />
                ) : (
                  <AssistantBubble
                    key={message.id}
                    content={message.content}
                    citations={message.citations ?? []}
                    actions={<AnswerVoiceButton answerKey={message.id} text={message.content} />}
                  />
                ),
              )}
              {pending && (
                <>
                  <UserBubble content={pending.question} />
                  <AssistantBubble
                    content={pending.answer}
                    citations={pending.citations}
                    streaming={pending.status === 'streaming'}
                    error={pending.error}
                    actions={
                      voiceState.speakingKey === STREAMING_ANSWER ? (
                        <AnswerVoiceButton answerKey={STREAMING_ANSWER} text={pending.answer} />
                      ) : undefined
                    }
                  />
                  {pending.status === 'error' && (
                    <div className="flex justify-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          const question = pending.question
                          stream.dismiss()
                          void send(question)
                        }}
                      >
                        <RotateCcw aria-hidden /> Try again
                      </Button>
                      <Button size="sm" variant="ghost" onClick={stream.dismiss}>
                        Dismiss
                      </Button>
                    </div>
                  )}
                </>
              )}
              <div ref={bottom} />
            </div>
          )}
        </div>

        <div className="mx-auto w-full max-w-3xl pt-3">
          <div className="mb-2 flex items-center gap-2">
            <FileText className="size-3.5 text-subtle" aria-hidden />
            <Select
              value={scope}
              onValueChange={(value) => {
                const next = new URLSearchParams(params)
                if (value === ALL_DOCUMENTS) next.delete('document')
                else next.set('document', value)
                setParams(next, { replace: true })
              }}
            >
              <SelectTrigger
                size="sm"
                className="h-7 max-w-64 border-dashed text-[11px]"
                aria-label="Answer from"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_DOCUMENTS}>Answer from all documents</SelectItem>
                {readyDocuments.map((document) => (
                  <SelectItem key={document.id} value={document.id}>
                    {document.filename}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {scope !== ALL_DOCUMENTS && (
              <Button
                variant="ghost"
                size="icon-xs"
                aria-label="Answer from all documents"
                onClick={() => {
                  const next = new URLSearchParams(params)
                  next.delete('document')
                  setParams(next, { replace: true })
                }}
              >
                <X />
              </Button>
            )}
            <div className="ml-auto">
              <ReadAloudToggle />
            </div>
          </div>
          <Composer
            onSend={(question, options) => void send(question, options)}
            onStop={stream.stop}
            streaming={stream.isStreaming}
            disabled={createConversation.isPending}
            autoFocus
          />
          <p className="mt-2 text-center text-[10px] text-subtle">
            Answers are generated from your documents and can be wrong. Check the sources.
          </p>
        </div>
      </section>
    </div>
  )
}

function NewChatIntro({ noDocuments, onPick }: { noDocuments: boolean; onPick: (question: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4 text-center">
      <BrandMark className="mb-5 size-12 rounded-2xl [&_svg]:w-7" />
      <h2 className="text-xl font-bold tracking-[-0.5px]">Ask anything about your documents</h2>
      <p className="mt-2 max-w-md text-[13px] text-muted-foreground">
        Answers are grounded in what you've uploaded, with the document and page for every source.
      </p>
      {noDocuments ? (
        <div className="mt-6 rounded-[12px] border border-warning/30 bg-warning-soft px-4 py-3 text-xs text-warning">
          You don't have any processed documents yet.{' '}
          <Link to={ROUTES.documents} className="font-semibold underline">
            Upload a PDF
          </Link>{' '}
          to get started.
        </div>
      ) : (
        <div className="mt-7 grid w-full max-w-xl gap-2 sm:grid-cols-3">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => onPick(suggestion)}
              className="flex items-start gap-2 rounded-[12px] border bg-card p-3 text-left text-xs leading-relaxed text-foreground/80 shadow-card hover:border-primary/40 hover:bg-accent"
            >
              <Sparkles className="mt-0.5 size-3.5 shrink-0 text-primary" aria-hidden />
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
