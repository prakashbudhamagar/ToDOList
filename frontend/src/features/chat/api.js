// Chat with the Gemini-backed assistant (key stays server-side in backend/.env).
import { request } from '../../shared/api/client.js'

export const sendChatMessage = (message, history) =>
  request('/chat/', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  })