import { request } from '../../shared/api/client'

export interface ChatMessage {
  role: 'user' | 'model'
  text: string
}

export interface ChatAction {
  tool: string
  result: unknown
}

export interface ChatReply {
  reply: string
  actions: ChatAction[]
}

export const sendChatMessage = (message: string, history: ChatMessage[]): Promise<ChatReply> =>
  request<ChatReply>('/chat/', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  })
