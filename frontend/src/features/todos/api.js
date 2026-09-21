// One function per /api/todos/ endpoint.
import { request } from '../../shared/api/client.js'

// The tasks come back ordered by priority (high first), then oldest first.
export const listTodos = () => request('/todos/')

export const createTodo = (title, priority) =>
  request('/todos/', { method: 'POST', body: JSON.stringify({ title, priority }) })

// PATCH only sends the fields we changed, so the others - and the task's
// create_at - are preserved by the backend.
export const updateTodo = (id, fields) =>
  request(`/todos/${id}/`, { method: 'PATCH', body: JSON.stringify(fields) })

export const deleteTodo = (id) => request(`/todos/${id}/`, { method: 'DELETE' })