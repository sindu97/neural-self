import { useSyncExternalStore } from 'react'

import { voice, type VoiceState } from '../tts/voice-controller'

/** Voice state for rendering; call methods on the returned controller. */
export function useVoice(): { state: VoiceState; voice: typeof voice } {
  const state = useSyncExternalStore(voice.subscribe, voice.getSnapshot)
  return { state, voice }
}
