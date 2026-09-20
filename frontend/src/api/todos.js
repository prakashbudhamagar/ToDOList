// One function per /api/todos/ endpoint.
import { request } from './client.js'

export const listTodos = () => request('/todos/')

export const createTodo = (title) =>
  request('/todos/', { method: 'POST', body: JSON.stringify({ title }) })

// PATCH only sends the fields we changed, so the task's create_at is preserved.
export const updateTodo = (id, title) =>
  request(`/todos/${id}/`, { method: 'PATCH', body: JSON.stringify({ title }) })

export const deleteTodo = (id) => request(`/todos/${id}/`, { method: 'DELETE' })

// Chat with the Gemini-backed assistant (key stays server-side in backend/.env).
export const sendChatMessage = (message, history) =>
  request('/chat/', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  })
