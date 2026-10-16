import { Mic, Square } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

import type { SpeechToText } from '../stt/use-speech-to-text'
import { voice } from '../tts/voice-controller'

/** Mic inside the question box: tap to speak, tap again to send now. */
export function MicButton({ stt, disabled }: { stt: SpeechToText; disabled?: boolean }) {
  if (!stt.isSupported) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span>
            <Button size="icon-sm" variant="ghost" disabled aria-label="Voice input unavailable">
              <Mic />
            </Button>
          </span>
        </TooltipTrigger>
        <TooltipContent>Voice input isn't supported in this browser. Try Chrome or Edge.</TooltipContent>
      </Tooltip>
    )
  }

  const label = stt.isListening ? 'Stop and send' : 'Ask by voice'
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          disabled={disabled}
          aria-label={label}
          aria-pressed={stt.isListening}
          // Start loading the voice as soon as the user reaches for the mic,
          // so it's ready by the time the answer arrives.
          onPointerEnter={() => voice.prepare()}
          onClick={() => {
            if (stt.isListening) return stt.finish()
            voice.unlock() // inside the click: allowed to start audio later
            voice.prepare()
            stt.start()
          }}
          className={cn(
            'text-subtle hover:text-primary',
            stt.isListening &&
              'bg-destructive-soft text-destructive hover:bg-destructive-soft hover:text-destructive',
          )}
        >
          {stt.isListening ? (
            <span className="relative grid place-items-center">
              <span className="absolute size-6 animate-ping rounded-full bg-destructive/20" aria-hidden />
              <Square className="size-3 fill-current" />
            </span>
          ) : (
            <Mic />
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}
