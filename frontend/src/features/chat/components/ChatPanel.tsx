import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { errorMessage } from '../../../shared/api/client'
import { sendChatMessage } from '../api'
import type { ChatMessage } from '../api'

import './ChatPanel.scss'

// SpeechRecognition itself is missing from lib.dom.d.ts (only its event types are
// declared), and Chrome/Edge expose it as SpeechRecognition, Safari with the
// webkit prefix.
interface SpeechRecognitionLike extends EventTarget {
  lang: string
  interimResults: boolean
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onend: ((event: Event) => void) | null
  start(): void
  stop(): void
  abort(): void
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}

function speechRecognitionConstructor(): SpeechRecognitionConstructor | undefined {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition
}

export interface ChatPanelProps {
  onTasksChanged: () => Promise<void>
}

export default function ChatPanel({ onTasksChanged }: ChatPanelProps) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'model',
      text: 'Hi! I can add, edit, delete and recommend tasks. Try "add buy milk as high priority" or "what should I do next?" and I will tell you how long each task may take.',
    },
  ])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [listening, setListening] = useState(false)
  const [voiceSupported, setVoiceSupported] = useState(false)
  const [spokenReplies, setSpokenReplies] = useState(true)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)

  useEffect(() => {
    if (speechRecognitionConstructor() && window.speechSynthesis) {
      setVoiceSupported(true)
    }
    return () => {
      recognitionRef.current?.abort()
      window.speechSynthesis?.cancel()
    }
  }, [])

  function speak(text: string) {
    if (!spokenReplies || !window.speechSynthesis) {
      return
    }
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
  }

  function toggleListening() {
    if (listening) {
      recognitionRef.current?.stop()
      return
    }
    const Recognition = speechRecognitionConstructor()
    if (!Recognition) {
      setError('Voice input is not supported in this browser - try Chrome or Edge.')
      return
    }
    const recognition = new Recognition()
    recognition.lang = 'en-US'
    recognition.interimResults = true
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join('')
      setDraft(transcript)
      if (event.results[event.results.length - 1].isFinal) {
        setListening(false)
      }
    }
    recognition.onerror = (event) => {
      setListening(false)
      if (event.error === 'not-allowed') {
        setError('Microphone access was blocked - allow it in the browser to use voice input.')
      } else if (event.error !== 'aborted') {
        setError(`Voice input failed: ${event.error}.`)
      }
    }
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    setError(null)
    recognition.start()
    setListening(true)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || sending) {
      return
    }
    recognitionRef.current?.stop()
    const nextMessages: ChatMessage[] = [...messages, { role: 'user', text }]
    setMessages(nextMessages)
    setDraft('')
    setSending(true)
    setError(null)
    try {
      const history = nextMessages.slice(-7, -1)
      const { reply, actions } = await sendChatMessage(text, history)
      setMessages([...nextMessages, { role: 'model', text: reply }])
      speak(reply)
      if (actions.length > 0) {
        await onTasksChanged()
      }
    } catch (err) {
      setError(`Could not reach the assistant: ${errorMessage(err)}`)
    } finally {
      setSending(false)
    }
  }

  if (!open) {
    return (
      <button type="button" className="chat-fab" onClick={() => setOpen(true)}>
        Chat
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Task assistant">
      <header className="chat-header">
        <strong>Task assistant</strong>
        <span className="chat-toggles">
          <label className="chat-toggle">
            <input
              type="checkbox"
              checked={spokenReplies}
              onChange={(event) => {
                setSpokenReplies(event.target.checked)
                if (!event.target.checked) {
                  window.speechSynthesis?.cancel()
                }
              }}
            />
            Speak replies
          </label>
          <button type="button" className="secondary" onClick={() => setOpen(false)}>
            Close
          </button>
        </span>
      </header>
      <div className="chat-messages">
        {messages.map((msg, index) => (
          <p key={index} className={`chat-bubble ${msg.role}`}>
            {msg.text}
          </p>
        ))}
        {sending && <p className="chat-bubble model typing">Thinking…</p>}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={draft}
          maxLength={2000}
          placeholder={listening ? 'Listening… speak now' : 'Ask me to add, list or recommend tasks…'}
          aria-label="Message the assistant"
          onChange={(event) => setDraft(event.target.value)}
        />
        {voiceSupported && (
          <button
            type="button"
            className={listening ? 'danger' : 'secondary'}
            onClick={toggleListening}
            aria-label={listening ? 'Stop listening' : 'Speak your message'}
          >
            {listening ? 'Stop' : 'Speak'}
          </button>
        )}
        <button type="submit" disabled={sending || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
