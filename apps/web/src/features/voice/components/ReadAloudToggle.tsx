import { Volume2, VolumeX } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

import { useVoice } from '../hooks/use-voice'

/** Read every answer aloud (answers to spoken questions are always read). */
export function ReadAloudToggle() {
  const { state, voice } = useVoice()
  const on = state.autoRead
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          size="sm"
          variant="ghost"
          className={on ? 'h-7 text-[11px] text-primary' : 'h-7 text-[11px] text-subtle'}
          aria-pressed={on}
          onClick={() => {
            voice.unlock()
            if (!on) voice.prepare()
            voice.setAutoRead(!on)
          }}
        >
          {on ? <Volume2 /> : <VolumeX />} Read answers aloud: {on ? 'On' : 'Off'}
        </Button>
      </TooltipTrigger>
      <TooltipContent>Answers to questions you ask by voice are always read aloud.</TooltipContent>
    </Tooltip>
  )
}
