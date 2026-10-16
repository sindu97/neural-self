import { Loader2, Volume2, VolumeX } from 'lucide-react'

import { Button } from '@/components/ui/button'

import { useVoice } from '../hooks/use-voice'

/** On each answer: "Listen" reads it aloud; while it plays, "Mute" stops it. */
export function AnswerVoiceButton({ answerKey, text }: { answerKey: string; text: string }) {
  const { state, voice } = useVoice()
  const speaking = state.speakingKey === answerKey
  const loading = speaking && state.modelStatus === 'loading'

  if (speaking) {
    return (
      <Button
        size="xs"
        variant="ghost"
        className="text-primary"
        onClick={() => voice.stop()}
        aria-label="Mute answer"
      >
        {loading ? <Loader2 className="animate-spin" /> : <VolumeX />}
        {loading
          ? `Preparing voice${state.progress ? ` ${Math.round(state.progress * 100)}%` : '…'}`
          : 'Mute'}
      </Button>
    )
  }
  return (
    <Button
      size="xs"
      variant="ghost"
      className="text-subtle hover:text-primary"
      disabled={!text.trim()}
      onClick={() => {
        voice.unlock()
        voice.speak(answerKey, text)
      }}
      aria-label="Listen to answer"
    >
      <Volume2 /> Listen
    </Button>
  )
}
